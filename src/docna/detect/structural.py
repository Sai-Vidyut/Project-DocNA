"""Structural detection of question candidates and answer-space relationships."""

from __future__ import annotations

import re

from docna.detect.content_policy import (
    is_discussion_only_marker,
    is_section_label_line,
    is_tick_response_value,
    is_worksheet_structure_label,
    looks_like_narrative_prose,
)
from docna.detect.models import StructuralCandidate, StructuralDetectionResult
from docna.ir import DocumentIR

QUESTION_MARK_RE = re.compile(r"\?\s*$")
NUMBERED_ITEM_RE = re.compile(r"^\s*\d+[\.\)]\s+.+", re.IGNORECASE)
Q_PREFIX_RE = re.compile(r"^\s*Q\s*\d+[\.\):]?\s+.+", re.IGNORECASE)
C_PREFIX_RE = re.compile(r"^\s*C\s*\d+[\.\):]\s+.+", re.IGNORECASE)
LETTER_SUBITEM_RE = re.compile(r"^\s*[a-zA-Z][\.\)]\s+.+")
IMPERATIVE_RE = re.compile(
    r"^\s*(explain|describe|define|list|outline|summarize|compare|contrast|identify|"
    r"state|name|implement|write|prove|create|calculate|discuss|analyze|evaluate|"
    r"demonstrate|tell|provide|give|document|draft|submit|review|select|choose|"
    r"specify|confirm|complete)\b",
    re.IGNORECASE,
)
PREFIXED_IMPERATIVE_RE = re.compile(
    r"^\s*(?:goal|item|task|question|part|step|section)\s*[\dIVXivx]+[\:\.\)]\s+"
    r"(explain|describe|define|list|outline|summarize|compare|contrast|identify|"
    r"state|name|implement|write|prove|create|calculate|discuss|analyze|evaluate|"
    r"demonstrate|tell|provide|give|document|draft|submit|review|select|choose|"
    r"specify|confirm)\b",
    re.IGNORECASE,
)
WH_PROMPT_NO_Q_RE = re.compile(
    r"^\s*(how|what|which|where|when|why|who)\b"
    r"(?:\s+\w+){0,8}\s+"
    r"(?:do|does|did|should|would|can|could|will|is|are|was|were|have|has|had)\b",
    re.IGNORECASE,
)
WH_FRAGMENT_RE = re.compile(
    r"^\s*(why|what|which|where|when|who)\s+(?:\w+\s+){0,5}\w+\s*$",
    re.IGNORECASE,
)
FORM_FIELD_PROMPT_RE = re.compile(
    r"^\s*(?:date|name|signature|supervisor|department|email|phone|address|title|"
    r"id|reg\.?\s*no|branch\s*/?\s*sec|shift|role|comments?)\b[\w\s\-/\.]*\??\s*$",
    re.IGNORECASE,
)
NUMBERED_IMPERATIVE_RE = re.compile(
    r"^\s*\d+[\.\)]\s+(explain|describe|define|list|outline|summarize|compare|contrast|"
    r"identify|state|name|implement|write|prove|create|calculate|discuss|analyze|evaluate|"
    r"demonstrate|tell|provide|give|document|draft|submit|review|select|choose|specify|confirm)\b",
    re.IGNORECASE,
)
EXERCISE_ITEM_RE = re.compile(r"^\s*(exercise|problem)\s+\d+\s*:", re.IGNORECASE)
BONUS_ITEM_RE = re.compile(r"^\s*bonus\s*:", re.IGNORECASE)
EXAMPLE_QUESTION_RE = re.compile(r"^\s*question\s*:", re.IGNORECASE)
WHAT_HOW_WHY_RE = re.compile(
    r"^\s*(what|how|why|when|where|who|which)\b.+\?\s*$",
    re.IGNORECASE,
)
FILL_BLANK_INLINE_RE = re.compile(r"_{3,}|\.{3,}|-{3,}")
INSTRUCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*complete all\b", re.IGNORECASE),
    re.compile(r"^\s*do not write\b", re.IGNORECASE),
    re.compile(r"^\s*answer all questions\b", re.IGNORECASE),
    re.compile(r"^\s*use complete sentences\b", re.IGNORECASE),
    re.compile(r"^\s*for office use only\b", re.IGNORECASE),
    re.compile(r"^\s*do not complete\b", re.IGNORECASE),
    re.compile(r"^\s*instructions?\s*:\s*$", re.IGNORECASE),
    re.compile(r"^\s*please answer every\b", re.IGNORECASE),
    re.compile(r"\bfor each (prompt|question|item|field|section)\b", re.IGNORECASE),
    re.compile(r"\bbrief reflection for each\b", re.IGNORECASE),
)
ANSWER_LABEL_RE = re.compile(r"^\s*answer\s*:\s*.+", re.IGNORECASE)
EXAMPLE_LABEL_RE = re.compile(r"^\s*example\s*:\s*$", re.IGNORECASE)
EXAMPLE_SECTION_START_RE = re.compile(
    r"^\s*example(?:\s+\w+)+\s*:?\s*$",
    re.IGNORECASE,
)


def detect_structural(ir: DocumentIR) -> StructuralDetectionResult:
    """Identify structural task candidates and answer-space relationships."""
    block_order = {block.block_id: index for index, block in enumerate(ir.blocks)}
    space_bindings = _bind_answer_spaces(ir, block_order)
    candidates: list[StructuralCandidate] = []
    instructions: list[StructuralCandidate] = []
    excluded_blocks: dict[str, str] = {}
    in_reference_sample = False

    for index, block in enumerate(ir.blocks):
        text = block.text.strip()
        if not text and block.kind != "table_cell":
            continue

        if text and FILL_BLANK_INLINE_RE.fullmatch(text):
            continue

        signals = _collect_signals(block, text)

        if EXAMPLE_LABEL_RE.match(text) or EXAMPLE_SECTION_START_RE.match(text):
            excluded_blocks[block.block_id] = "example_label"
            in_reference_sample = True
            continue

        if in_reference_sample:
            if _is_reference_sample_boundary(text, signals, block):
                in_reference_sample = False
            else:
                reason = "example_reference"
                if EXAMPLE_QUESTION_RE.match(text) or ANSWER_LABEL_RE.match(text):
                    reason = "example_reference"
                elif not EXAMPLE_QUESTION_RE.match(text) and not ANSWER_LABEL_RE.match(text):
                    reason = "example_sample"
                excluded_blocks[block.block_id] = reason
                continue

        if _looks_like_instruction(text, signals):
            instructions.append(
                StructuralCandidate(
                    block_id=block.block_id,
                    provisional_kind="instruction",
                    prompt_text=text,
                    confidence=_instruction_confidence(signals),
                    signals=signals,
                    context_block_ids=_neighbor_context(ir.blocks, index),
                )
            )
            continue

        if is_discussion_only_marker(text) or is_section_label_line(text):
            excluded_blocks[block.block_id] = "discussion_marker"
            continue

        if looks_like_narrative_prose(text):
            excluded_blocks[block.block_id] = "narrative_prose"
            continue

        if block.kind == "table_cell" and _table_cell_is_question(ir, block, index):
            space_id, ambiguous = _space_for_block(block.block_id, space_bindings)
            candidates.append(
                StructuralCandidate(
                    block_id=block.block_id,
                    provisional_kind="table_item",
                    prompt_text=text,
                    confidence=0.75 if signals else 0.65,
                    signals=signals or ["table_cell"],
                    suggested_answer_space_id=space_id,
                    parent_block_id=block.parent_block_id,
                    context_block_ids=_neighbor_context(ir.blocks, index),
                    ambiguous_space=ambiguous,
                )
            )
            continue

        if ANSWER_LABEL_RE.match(text) and not _is_placeholder_answer(text):
            excluded_blocks[block.block_id] = "answer_provided"
            continue

        if EXAMPLE_LABEL_RE.match(text):
            excluded_blocks[block.block_id] = "example_label"
            continue

        if EXAMPLE_QUESTION_RE.match(text):
            excluded_blocks[block.block_id] = "example_reference"
            continue

        if _is_example_question(ir, index, text):
            excluded_blocks[block.block_id] = "example_reference"
            continue

        if block.kind == "heading":
            excluded_blocks[block.block_id] = "worksheet_label"
            continue

        if is_worksheet_structure_label(text) or is_tick_response_value(text):
            excluded_blocks[block.block_id] = "worksheet_label"
            continue

        provisional_kind, confidence = _classify_candidate(block, text, signals)
        if provisional_kind is None:
            continue

        followup_status, _followup_text = _answer_followup_status(ir, index)
        segment_texts = _split_independent_task_segments(text)
        if not segment_texts:
            continue

        for segment_text in segment_texts:
            segment_kind, segment_confidence = _classify_candidate(
                block,
                segment_text,
                _collect_signals(block, segment_text),
            )
            if segment_kind is None:
                continue

            space_id, ambiguous = _space_for_block(block.block_id, space_bindings)
            parent_block_id = _parent_block_for_candidate(ir, index, segment_kind)
            segment_signals = list(_collect_signals(block, segment_text))
            if followup_status == "filled":
                segment_signals.append("already_answered")

            candidates.append(
                StructuralCandidate(
                    block_id=block.block_id,
                    provisional_kind=segment_kind,
                    prompt_text=segment_text,
                    confidence=segment_confidence,
                    signals=segment_signals,
                    suggested_answer_space_id=space_id,
                    parent_block_id=parent_block_id,
                    context_block_ids=_neighbor_context(ir.blocks, index),
                    ambiguous_space=ambiguous,
                )
            )

    candidates.extend(_table_row_candidates(ir, space_bindings, block_order))

    return StructuralDetectionResult(
        candidates=candidates,
        instruction_candidates=instructions,
        excluded_blocks=excluded_blocks,
    )


def _collect_signals(block, text: str) -> list[str]:
    signals: list[str] = []
    if QUESTION_MARK_RE.search(text):
        signals.append("question_mark")
    if NUMBERED_ITEM_RE.match(text):
        signals.append("numbered_item")
    if Q_PREFIX_RE.match(text):
        signals.append("q_prefix")
    if C_PREFIX_RE.match(text):
        signals.append("c_prefix")
    if LETTER_SUBITEM_RE.match(text):
        signals.append("letter_subitem")
    if NUMBERED_IMPERATIVE_RE.match(text):
        signals.append("numbered_imperative")
    if EXERCISE_ITEM_RE.match(text):
        signals.append("exercise_item")
    if BONUS_ITEM_RE.match(text):
        signals.append("bonus_item")
    if IMPERATIVE_RE.match(text):
        signals.append("imperative")
    if PREFIXED_IMPERATIVE_RE.match(text):
        signals.append("prefixed_imperative")
    if WH_PROMPT_NO_Q_RE.match(text):
        signals.append("wh_prompt_no_q")
    if WH_FRAGMENT_RE.match(text):
        signals.append("wh_fragment")
    if FORM_FIELD_PROMPT_RE.match(text):
        signals.append("form_field_prompt")
    if WHAT_HOW_WHY_RE.match(text):
        signals.append("wh_question")
    if FILL_BLANK_INLINE_RE.search(text):
        signals.append("inline_blank")
    if block.kind == "list_item":
        signals.append("list_item")
    if block.kind == "heading":
        signals.append("heading")
    if block.kind == "table_cell":
        signals.append("table_cell")
    return signals


def _is_reference_sample_boundary(text: str, signals: list[str], block) -> bool:
    if block.kind == "heading":
        return True
    if EXERCISE_ITEM_RE.match(text):
        return True
    if BONUS_ITEM_RE.match(text):
        return True
    if NUMBERED_ITEM_RE.match(text) and (
        "question_mark" in signals
        or "imperative" in signals
        or "wh_question" in signals
        or "numbered_imperative" in signals
    ):
        return True
    if EXAMPLE_LABEL_RE.match(text) or EXAMPLE_SECTION_START_RE.match(text):
        return True
    return False


def _looks_like_instruction(text: str, signals: list[str]) -> bool:
    if "heading" in signals:
        return False
    if QUESTION_MARK_RE.search(text):
        return False
    return any(pattern.search(text) for pattern in INSTRUCTION_PATTERNS)


def _instruction_confidence(signals: list[str]) -> float:
    return 0.85 if signals else 0.7


def _classify_candidate(block, text: str, signals: list[str]) -> tuple[str | None, float]:
    if looks_like_narrative_prose(text) or is_discussion_only_marker(text):
        return None, 0.0

    if EXERCISE_ITEM_RE.match(text):
        return "question", 0.88

    if "c_prefix" in signals or C_PREFIX_RE.match(text):
        return "question", 0.88

    if "q_prefix" in signals:
        return "question", 0.88

    if BONUS_ITEM_RE.match(text):
        return "question", 0.82

    if "prefixed_imperative" in signals or PREFIXED_IMPERATIVE_RE.match(text):
        return "question", 0.82

    if "numbered_imperative" in signals:
        return "question", 0.85

    if FILL_BLANK_INLINE_RE.search(text) and not QUESTION_MARK_RE.search(text):
        return "fill_blank", 0.8

    if LETTER_SUBITEM_RE.match(text):
        return "sub_question", 0.82

    if block.kind == "list_item" and (block.list_level or 0) > 0:
        if any(
            s in signals
            for s in ("question_mark", "imperative", "wh_question", "wh_prompt_no_q", "wh_fragment")
        ):
            return "sub_question", 0.82

    if block.kind == "table_cell":
        return None, 0.0

    if _is_strong_task_signal(text, signals):
        return "question", _task_confidence_for_signals(signals)

    score = 0.0
    if "question_mark" in signals:
        score += 0.35
    if "numbered_item" in signals or "q_prefix" in signals:
        score += 0.25
    if "imperative" in signals or "wh_question" in signals or "wh_prompt_no_q" in signals or "wh_fragment" in signals:
        score += 0.25
    if "form_field_prompt" in signals:
        score += 0.30
    if "list_item" in signals:
        score += 0.1
    if "inline_blank" in signals:
        score += 0.15
    if "numbered_imperative" in signals:
        score += 0.35
    if "exercise_item" in signals:
        score += 0.35

    if score >= 0.35:
        return "question", min(0.95, 0.55 + score)
    return None, 0.0


def _is_strong_task_signal(text: str, signals: list[str]) -> bool:
    if "q_prefix" in signals or "c_prefix" in signals:
        return True
    if "prefixed_imperative" in signals:
        return True
    if "wh_prompt_no_q" in signals and not looks_like_narrative_prose(text):
        return True
    if "wh_fragment" in signals and not looks_like_narrative_prose(text):
        return True
    if "imperative" in signals and _imperative_reads_as_task(text):
        return True
    if "form_field_prompt" in signals:
        return True
    return False


def _imperative_reads_as_task(text: str) -> bool:
    if looks_like_narrative_prose(text):
        return False
    stripped = text.strip()
    if not IMPERATIVE_RE.match(stripped) and not PREFIXED_IMPERATIVE_RE.match(stripped):
        return False
    word_count = len(stripped.split())
    return word_count <= 30


def _task_confidence_for_signals(signals: list[str]) -> float:
    if "prefixed_imperative" in signals:
        return 0.82
    if "wh_prompt_no_q" in signals:
        return 0.80
    if "wh_fragment" in signals:
        return 0.78
    if "form_field_prompt" in signals:
        return 0.78
    if "imperative" in signals:
        return 0.78
    return 0.76


def _split_independent_task_segments(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    if QUESTION_MARK_RE.search(stripped) and stripped.count("?") <= 1:
        return [stripped]

    parts = re.split(r"(?<=[.!?])\s+", stripped)
    if len(parts) <= 1:
        return [stripped]

    segments: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        signals = _collect_signals_for_text(part)
        if _segment_looks_like_task(part, signals):
            segments.append(part)

    if len(segments) > 1:
        return segments
    return [stripped]


def _collect_signals_for_text(text: str) -> list[str]:
    signals: list[str] = []
    if QUESTION_MARK_RE.search(text):
        signals.append("question_mark")
    if IMPERATIVE_RE.match(text):
        signals.append("imperative")
    if PREFIXED_IMPERATIVE_RE.match(text):
        signals.append("prefixed_imperative")
    if WH_PROMPT_NO_Q_RE.match(text):
        signals.append("wh_prompt_no_q")
    if WH_FRAGMENT_RE.match(text):
        signals.append("wh_fragment")
    if WHAT_HOW_WHY_RE.match(text):
        signals.append("wh_question")
    if FORM_FIELD_PROMPT_RE.match(text):
        signals.append("form_field_prompt")
    if FILL_BLANK_INLINE_RE.search(text):
        signals.append("inline_blank")
    return signals


def _segment_looks_like_task(text: str, signals: list[str]) -> bool:
    if looks_like_narrative_prose(text) or is_discussion_only_marker(text):
        return False
    kind, _confidence = _classify_candidate_for_text(text, signals)
    return kind is not None


def _classify_candidate_for_text(text: str, signals: list[str]) -> tuple[str | None, float]:
    class _Block:
        kind = "paragraph"
        list_level = None

    return _classify_candidate(_Block(), text, signals)


def _answer_followup_status(ir: DocumentIR, index: int) -> tuple[str | None, str | None]:
    for offset in range(1, 4):
        if index + offset >= len(ir.blocks):
            break
        next_block = ir.blocks[index + offset]
        next_text = next_block.text.strip()
        if not next_text:
            continue
        if ANSWER_LABEL_RE.match(next_text):
            if _is_placeholder_answer(next_text):
                return "empty", None
            answer_text = re.sub(
                r"^\s*answer\s*:\s*",
                "",
                next_text,
                flags=re.IGNORECASE,
            ).strip()
            return "filled", answer_text
        break
    return None, None


def _table_cell_is_question_by_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped or is_worksheet_structure_label(stripped):
        return False
    return bool(
        QUESTION_MARK_RE.search(stripped)
        or IMPERATIVE_RE.match(stripped)
        or PREFIXED_IMPERATIVE_RE.match(stripped)
        or WH_PROMPT_NO_Q_RE.match(stripped)
        or WHAT_HOW_WHY_RE.match(stripped)
    )


def _table_cell_is_question(ir: DocumentIR, block, index: int) -> bool:
    text = block.text.strip()
    if not text:
        return False
    if block.text.strip() and _is_answer_column(ir, block):
        return False
    return bool(
        QUESTION_MARK_RE.search(text)
        or IMPERATIVE_RE.match(text)
        or PREFIXED_IMPERATIVE_RE.match(text)
        or WH_PROMPT_NO_Q_RE.match(text)
        or WH_FRAGMENT_RE.match(text)
        or WHAT_HOW_WHY_RE.match(text)
    )


def _is_answer_column(ir: DocumentIR, block) -> bool:
    for table in ir.tables:
        for row in table.rows:
            if block.block_id not in row:
                continue
            col_index = row.index(block.block_id)
            if table.header_row and col_index > 0:
                header_block_id = row[0]
                header = _block_text(ir, header_block_id).lower()
                if "answer" in header:
                    return True
    return False


def _block_text(ir: DocumentIR, block_id: str) -> str:
    for block in ir.blocks:
        if block.block_id == block_id:
            return block.text
    return ""


def _is_example_question(ir: DocumentIR, index: int, text: str) -> bool:
    if not EXAMPLE_QUESTION_RE.match(text):
        return False
    for prior in reversed(ir.blocks[:index]):
        prior_text = prior.text.strip().lower()
        if not prior_text:
            continue
        if prior_text.startswith("example"):
            return True
        return False
    return False


def _is_placeholder_answer(text: str) -> bool:
    after_label = re.sub(r"^\s*answer\s*:\s*", "", text, flags=re.IGNORECASE).strip()
    if not after_label:
        return True
    return bool(FILL_BLANK_INLINE_RE.fullmatch(after_label))


def _parent_block_for_candidate(ir: DocumentIR, index: int, kind: str) -> str | None:
    block = ir.blocks[index]
    if kind != "sub_question":
        return None

    text = block.text.strip()
    if LETTER_SUBITEM_RE.match(text):
        for prior in reversed(ir.blocks[:index]):
            prior_text = prior.text.strip()
            if LETTER_SUBITEM_RE.match(prior_text):
                return prior.block_id
            if QUESTION_MARK_RE.search(prior_text) and not LETTER_SUBITEM_RE.match(prior_text):
                return prior.block_id

    if block.parent_block_id:
        return block.parent_block_id

    for prior in reversed(ir.blocks[:index]):
        if prior.kind == "list_item" and (prior.list_level or 0) < (block.list_level or 0):
            return prior.block_id
        if QUESTION_MARK_RE.search(prior.text):
            return prior.block_id
    return None


def _neighbor_context(blocks, index: int, radius: int = 2) -> list[str]:
    start = max(0, index - radius)
    end = min(len(blocks), index + radius + 1)
    return [blocks[i].block_id for i in range(start, end) if i != index]


def _table_row_prompt_index(texts: list[str], empty_indices: list[int]) -> int:
    for idx, text in enumerate(texts):
        stripped = text.strip()
        if not stripped or idx in empty_indices or is_worksheet_structure_label(stripped):
            continue
        if _table_cell_is_question_by_text(stripped) or FORM_FIELD_PROMPT_RE.match(stripped):
            return idx
    for idx, text in enumerate(texts):
        stripped = text.strip()
        if stripped and idx not in empty_indices and not is_worksheet_structure_label(stripped):
            if len(stripped) >= 3:
                return idx
    return -1


def _table_row_candidates(
    ir: DocumentIR,
    space_bindings: dict[str, tuple[str | None, bool]],
    block_order: dict[str, int],
) -> list[StructuralCandidate]:
    candidates: list[StructuralCandidate] = []
    seen_blocks: set[str] = set()

    for table in ir.tables:
        for row_index, row in enumerate(table.rows):
            if table.header_row and row_index == 0:
                continue
            texts = [_block_text(ir, block_id) for block_id in row]
            if len(row) < 2:
                continue
            empty_indices = [idx for idx, text in enumerate(texts) if not text.strip()]
            if not empty_indices:
                continue
            prompt_index = _table_row_prompt_index(texts, empty_indices)
            if prompt_index < 0:
                continue
            prompt_block_id = row[prompt_index]
            if prompt_block_id in seen_blocks:
                continue
            empty_block_id = row[empty_indices[-1]]
            space_id, ambiguous = space_bindings.get(empty_block_id, (None, False))
            index = block_order.get(prompt_block_id, 0)
            candidates.append(
                StructuralCandidate(
                    block_id=prompt_block_id,
                    provisional_kind="table_item",
                    prompt_text=texts[prompt_index].strip(),
                    confidence=0.78,
                    signals=["table_row_pair"],
                    suggested_answer_space_id=space_id,
                    context_block_ids=_neighbor_context(ir.blocks, index),
                    ambiguous_space=ambiguous,
                )
            )
            seen_blocks.add(prompt_block_id)

    return candidates


def _bind_answer_spaces(
    ir: DocumentIR,
    block_order: dict[str, int],
) -> dict[str, tuple[str | None, bool]]:
    """Map block_id -> (primary space_id, ambiguous_flag) without reading locators."""
    bindings: dict[str, tuple[str | None, bool]] = {
        block.block_id: (None, False) for block in ir.blocks
    }

    blank_spaces = [space for space in ir.answer_spaces if space.type == "blank_run"]
    for space in blank_spaces:
        for block in ir.blocks:
            if space.current_text and space.current_text in block.text:
                current, ambiguous = bindings[block.block_id]
                if current is None:
                    bindings[block.block_id] = (space.space_id, False)
                else:
                    bindings[block.block_id] = (current, True)

    empty_cell_blocks = [
        block.block_id
        for block in ir.blocks
        if block.kind == "table_cell" and not block.text.strip()
    ]
    table_spaces = [space for space in ir.answer_spaces if space.type == "table_cell"]
    for block_id, space in zip(empty_cell_blocks, table_spaces, strict=False):
        bindings[block_id] = (space.space_id, False)
    if len(table_spaces) > len(empty_cell_blocks):
        pass

    empty_para_spaces = [space for space in ir.answer_spaces if space.type == "empty_para"]
    space_index = 0
    for index, block in enumerate(ir.blocks):
        if index + 1 >= len(ir.blocks):
            continue
        next_block = ir.blocks[index + 1]
        if next_block.text.strip():
            continue
        if space_index >= len(empty_para_spaces):
            break
        space = empty_para_spaces[space_index]
        space_index += 1
        current, ambiguous = bindings[block.block_id]
        if current is None:
            bindings[block.block_id] = (space.space_id, False)
        else:
            bindings[block.block_id] = (current, True)

    content_spaces = [space for space in ir.answer_spaces if space.type == "content_control"]
    content_blocks = [
        block
        for block in ir.blocks
        if block.role_hint == "possible_blank" or _looks_like_placeholder_text(block.text)
    ]
    for block, space in zip(content_blocks, content_spaces, strict=False):
        bindings[block.block_id] = (space.space_id, False)

    return bindings


def _looks_like_placeholder_text(text: str) -> bool:
    lowered = text.strip().lower()
    return lowered in {"", "click or tap to enter text.", "type here"}


def _space_for_block(
    block_id: str,
    bindings: dict[str, tuple[str | None, bool]],
) -> tuple[str | None, bool]:
    return bindings.get(block_id, (None, False))
