"""Merge structural candidates with semantic classifications into Task objects."""

from __future__ import annotations

from docna.detect.config import DetectionConfig
from docna.detect.content_policy import (
    is_structural_exclusion_reason,
    is_tick_response_value,
    is_worksheet_structure_label,
    looks_like_ai_directed_text,
    normalize_prompt_text,
)
from docna.detect.structural import _neighbor_context
from docna.detect.models import (
    TASK_LIKE_KINDS,
    DetectionResult,
    SemanticClassificationItem,
    StructuralCandidate,
    StructuralDetectionResult,
    SemanticDetectionResult,
)
from docna.ir import DocumentIR, Task

TASK_KIND_MAP = {
    "question": "question",
    "sub_question": "sub_question",
    "fill_blank": "fill_blank",
    "table_item": "table_item",
    "instruction": "instruction",
}


def merge_detections(
    ir: DocumentIR,
    structural: StructuralDetectionResult,
    semantic: SemanticDetectionResult,
    *,
    config: DetectionConfig | None = None,
) -> DetectionResult:
    """Combine structural and semantic detection into final Task objects."""
    config = config or DetectionConfig()
    warnings = list(semantic.warnings)
    semantic_by_block = {item.block_id: item for item in semantic.classifications}
    structural_task_like = {
        candidate.block_id: candidate
        for candidate in structural.candidates
        if candidate.provisional_kind in TASK_LIKE_KINDS
    }
    structural_instruction_ids = {
        instruction.block_id for instruction in structural.instruction_candidates
    }

    tasks: list[Task] = []
    task_seq = 0
    block_to_task_id: dict[str, str] = {}
    seen_candidate_keys: set[tuple[str, str]] = set()
    seen_prompt_texts: set[str] = set()

    ordered_candidates = _ordered_candidates(structural)
    for candidate in ordered_candidates:
        candidate_key = (candidate.block_id, candidate.prompt_text.strip())
        if candidate_key in seen_candidate_keys:
            continue
        semantic_item = semantic_by_block.get(candidate.block_id)
        task, task_warnings = _build_task(
            ir=ir,
            candidate=candidate,
            semantic_item=semantic_item,
            config=config,
            task_seq=task_seq,
            block_to_task_id=block_to_task_id,
        )
        task_seq += 1
        warnings.extend(task_warnings)
        if task is not None:
            block_to_task_id[candidate.block_id] = task.task_id
            seen_candidate_keys.add(candidate_key)
            seen_prompt_texts.add(normalize_prompt_text(task.prompt_text))
            tasks.append(task)
        elif candidate.block_id in structural_task_like:
            seen_candidate_keys.add(candidate_key)

    for instruction in structural.instruction_candidates:
        if instruction.block_id in block_to_task_id:
            continue
        if _is_block_excluded(structural, instruction.block_id):
            continue
        semantic_item = semantic_by_block.get(instruction.block_id)
        if semantic_item and semantic_item.kind != "instruction":
            continue
        task, task_warnings = _build_instruction_task(
            instruction=instruction,
            semantic_item=semantic_item,
            task_seq=task_seq,
        )
        task_seq += 1
        warnings.extend(task_warnings)
        if task is not None:
            block_to_task_id[instruction.block_id] = task.task_id
            tasks.append(task)

    seen_block_ids = set(block_to_task_id.keys()) | {
        key[0] for key in seen_candidate_keys
    }

    for item in semantic.classifications:
        if item.block_id in seen_block_ids:
            continue
        if _is_block_excluded(structural, item.block_id):
            seen_block_ids.add(item.block_id)
            continue

        if item.kind in {"narrative"}:
            continue

        if item.kind == "instruction":
            block = _block_for_id(ir, item.block_id)
            if block is None:
                continue
            prompt_text = block.text.strip()
            if not _should_emit_semantic_instruction(
                block_id=item.block_id,
                prompt_text=prompt_text,
                structural=structural,
                structural_task_like=structural_task_like,
                structural_instruction_ids=structural_instruction_ids,
            ):
                seen_block_ids.add(item.block_id)
                continue
            task, task_warnings = _build_instruction_task(
                instruction=StructuralCandidate(
                    block_id=item.block_id,
                    provisional_kind="instruction",
                    prompt_text=prompt_text,
                    confidence=item.confidence,
                    signals=["semantic_only"],
                    context_block_ids=[],
                ),
                semantic_item=item,
                task_seq=task_seq,
            )
            task_seq += 1
            warnings.extend(task_warnings)
            if task is not None:
                seen_block_ids.add(item.block_id)
                tasks.append(task)
            continue

        if item.kind == "already_answered":
            block = _block_for_id(ir, item.block_id)
            if block is None:
                warnings.append(f"merge_unknown_block_id:{item.block_id}")
                continue
            task_id = _next_task_id(task_seq)
            task_seq += 1
            tasks.append(
                Task(
                    task_id=task_id,
                    kind="question",
                    prompt_text=block.text.strip(),
                    context_block_ids=[],
                    confidence=item.confidence,
                    skip_reason="already_answered",
                )
            )
            block_to_task_id[item.block_id] = task_id
            seen_block_ids.add(item.block_id)
            continue

        if item.kind in TASK_LIKE_KINDS:
            block = _block_for_id(ir, item.block_id)
            if block is None:
                warnings.append(f"merge_unknown_block_id:{item.block_id}")
                continue
            prompt_text = block.text.strip()
            normalized_prompt = normalize_prompt_text(prompt_text)
            if normalized_prompt in seen_prompt_texts:
                seen_block_ids.add(item.block_id)
                continue
            if is_worksheet_structure_label(prompt_text) or is_tick_response_value(prompt_text):
                seen_block_ids.add(item.block_id)
                continue
            block_index = _block_index(ir, item.block_id)
            candidate = StructuralCandidate(
                block_id=item.block_id,
                provisional_kind=item.kind,  # type: ignore[arg-type]
                prompt_text=prompt_text,
                confidence=item.confidence,
                signals=["semantic_only"],
                context_block_ids=_neighbor_context(ir.blocks, block_index),
            )
            task, task_warnings = _build_task(
                ir=ir,
                candidate=candidate,
                semantic_item=item,
                config=config,
                task_seq=task_seq,
                block_to_task_id=block_to_task_id,
            )
            task_seq += 1
            warnings.extend(task_warnings)
            if task is not None:
                block_to_task_id[item.block_id] = task.task_id
                seen_block_ids.add(item.block_id)
                seen_prompt_texts.add(normalize_prompt_text(task.prompt_text))
                tasks.append(task)

    return DetectionResult(tasks=tasks, warnings=warnings)


def _is_block_excluded(structural: StructuralDetectionResult, block_id: str) -> bool:
    reason = structural.excluded_blocks.get(block_id)
    return reason is not None and is_structural_exclusion_reason(reason)


def _should_emit_semantic_instruction(
    *,
    block_id: str,
    prompt_text: str,
    structural: StructuralDetectionResult,
    structural_task_like: dict[str, StructuralCandidate],
    structural_instruction_ids: set[str],
) -> bool:
    if block_id in structural_task_like:
        return False
    if looks_like_ai_directed_text(prompt_text):
        return False
    if block_id in structural_instruction_ids:
        return True
    return not looks_like_ai_directed_text(prompt_text)


def _ordered_candidates(structural: StructuralDetectionResult) -> list[StructuralCandidate]:
    return list(structural.candidates)


def _build_task(
    *,
    ir: DocumentIR,
    candidate: StructuralCandidate,
    semantic_item: SemanticClassificationItem | None,
    config: DetectionConfig,
    task_seq: int,
    block_to_task_id: dict[str, str],
) -> tuple[Task | None, list[str]]:
    warnings: list[str] = []
    block = _block_for_id(ir, candidate.block_id)
    if block is None:
        return None, [f"merge_missing_block:{candidate.block_id}"]

    if semantic_item is not None:
        if semantic_item.kind == "instruction":
            if candidate.provisional_kind in TASK_LIKE_KINDS:
                kind = candidate.provisional_kind
                confidence = max(candidate.confidence, semantic_item.confidence)
            else:
                return None, []
        elif semantic_item.kind == "already_answered" or "already_answered" in candidate.signals:
            return (
                Task(
                    task_id=_next_task_id(task_seq),
                    kind="question",
                    prompt_text=candidate.prompt_text,
                    parent_task_id=_resolve_parent_task_id(
                        candidate, block_to_task_id
                    ),
                    context_block_ids=candidate.context_block_ids,
                    answer_space_id=candidate.suggested_answer_space_id,
                    confidence=max(semantic_item.confidence, candidate.confidence),
                    skip_reason="already_answered",
                ),
                warnings,
            )
        elif semantic_item.kind == "narrative":
            if candidate.confidence >= 0.75 and candidate.provisional_kind in TASK_LIKE_KINDS:
                kind = candidate.provisional_kind
                confidence = max(candidate.confidence, semantic_item.confidence)
            else:
                return None, []
        else:
            kind = TASK_KIND_MAP.get(semantic_item.kind, candidate.provisional_kind)
            confidence = semantic_item.confidence
    else:
        if "already_answered" in candidate.signals:
            return (
                Task(
                    task_id=_next_task_id(task_seq),
                    kind="question",
                    prompt_text=candidate.prompt_text,
                    parent_task_id=_resolve_parent_task_id(
                        candidate, block_to_task_id
                    ),
                    context_block_ids=candidate.context_block_ids,
                    answer_space_id=candidate.suggested_answer_space_id,
                    confidence=candidate.confidence,
                    skip_reason="already_answered",
                ),
                warnings,
            )
        kind = candidate.provisional_kind
        confidence = candidate.confidence

    if kind == "instruction":
        return None, []

    skip_reason = _confidence_skip_reason(confidence, config, warnings, candidate.block_id)
    if skip_reason is None and "already_answered" in candidate.signals:
        skip_reason = "already_answered"

    if candidate.ambiguous_space:
        warnings.append(f"ambiguous_answer_space:{candidate.block_id}")

    parent_task_id = _resolve_parent_task_id(candidate, block_to_task_id)

    return (
        Task(
            task_id=_next_task_id(task_seq),
            kind=kind,  # type: ignore[arg-type]
            prompt_text=candidate.prompt_text,
            parent_task_id=parent_task_id,
            context_block_ids=candidate.context_block_ids,
            answer_space_id=candidate.suggested_answer_space_id,
            confidence=confidence,
            skip_reason=skip_reason,
        ),
        warnings,
    )


def _build_instruction_task(
    *,
    instruction: StructuralCandidate,
    semantic_item: SemanticClassificationItem | None,
    task_seq: int,
) -> tuple[Task | None, list[str]]:
    confidence = semantic_item.confidence if semantic_item else instruction.confidence
    return (
        Task(
            task_id=_next_task_id(task_seq),
            kind="instruction",
            prompt_text=instruction.prompt_text,
            context_block_ids=instruction.context_block_ids,
            confidence=confidence,
            skip_reason=None,
        ),
        [],
    )


def _confidence_skip_reason(
    confidence: float,
    config: DetectionConfig,
    warnings: list[str],
    block_id: str,
) -> str | None:
    if confidence < config.review_threshold:
        warnings.append(f"low_confidence:{block_id}:{confidence:.2f}")
        return "low_confidence"
    if confidence < config.safe_threshold:
        warnings.append(f"review_recommended:{block_id}:{confidence:.2f}")
    return None


def _resolve_parent_task_id(
    candidate: StructuralCandidate,
    block_to_task_id: dict[str, str],
) -> str | None:
    if not candidate.parent_block_id:
        return None
    if candidate.parent_block_id in block_to_task_id:
        parent_task = block_to_task_id[candidate.parent_block_id]
        return parent_task
    return None


def _block_for_id(ir: DocumentIR, block_id: str):
    for block in ir.blocks:
        if block.block_id == block_id:
            return block
    return None


def _block_index(ir: DocumentIR, block_id: str) -> int:
    for index, block in enumerate(ir.blocks):
        if block.block_id == block_id:
            return index
    return 0


def _next_task_id(task_seq: int) -> str:
    return f"task_{task_seq + 1:04d}"
