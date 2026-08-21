"""LLM semantic classification of document blocks."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import ValidationError

from docna.ai.port import AIProvider, ChatMessage
from docna.ai.prompts.semantic_classification import (
    SEMANTIC_CLASSIFICATION_SYSTEM_PROMPT,
    build_semantic_user_prompt,
)
from docna.detect.config import DetectionConfig
from docna.detect.models import (
    SemanticClassificationItem,
    SemanticClassificationResponse,
    SemanticDetectionResult,
)
from docna.ir import DocumentIR


def detect_semantic(
    ir: DocumentIR,
    preview: str,
    provider: AIProvider,
    *,
    config: DetectionConfig | None = None,
) -> SemanticDetectionResult:
    """Classify blocks using the AI provider. Classification only — no answers."""
    config = config or DetectionConfig()
    valid_block_ids = {block.block_id for block in ir.blocks}
    warnings: list[str] = []
    classifications: list[SemanticClassificationItem] = []

    for chunk in _chunk_preview(ir, preview, config):
        messages = [
            ChatMessage(role="system", content=SEMANTIC_CLASSIFICATION_SYSTEM_PROMPT),
            ChatMessage(role="user", content=build_semantic_user_prompt(chunk)),
        ]
        try:
            response = provider.complete(messages, SemanticClassificationResponse)
        except ValidationError as exc:
            error_type = exc.errors()[0]["type"] if exc.errors() else "validation_error"
            warnings.append(f"semantic_chunk_validation_error:{error_type}")
            continue
        except Exception as exc:  # noqa: BLE001 - safe handling for provider failures
            warnings.append(f"semantic_chunk_provider_error:{type(exc).__name__}")
            continue

        if not isinstance(response, SemanticClassificationResponse):
            warnings.append("semantic_chunk_unexpected_response_type")
            continue

        chunk_items, chunk_warnings = _validate_classifications(
            response.classifications,
            valid_block_ids,
        )
        classifications.extend(chunk_items)
        warnings.extend(chunk_warnings)

    deduped, dedupe_warnings = _dedupe_classifications(classifications)
    warnings.extend(dedupe_warnings)

    return SemanticDetectionResult(classifications=deduped, warnings=warnings)


def _validate_classifications(
    items: Sequence[SemanticClassificationItem],
    valid_block_ids: set[str],
) -> tuple[list[SemanticClassificationItem], list[str]]:
    accepted: list[SemanticClassificationItem] = []
    warnings: list[str] = []

    for item in items:
        try:
            validated = SemanticClassificationItem.model_validate(item.model_dump())
        except ValidationError:
            warnings.append("semantic_invalid_classification_item")
            continue

        if validated.block_id not in valid_block_ids:
            warnings.append(f"semantic_unknown_block_id:{validated.block_id}")
            continue

        accepted.append(validated)

    return accepted, warnings


def _dedupe_classifications(
    items: Sequence[SemanticClassificationItem],
) -> tuple[list[SemanticClassificationItem], list[str]]:
    seen: dict[str, SemanticClassificationItem] = {}
    warnings: list[str] = []

    for item in items:
        if item.block_id in seen:
            warnings.append(f"semantic_duplicate_block_id:{item.block_id}")
            if item.confidence > seen[item.block_id].confidence:
                seen[item.block_id] = item
            continue
        seen[item.block_id] = item

    return list(seen.values()), warnings


def _chunk_preview(ir: DocumentIR, preview: str, config: DetectionConfig) -> list[str]:
    lines = preview.splitlines()
    if not ir.outline:
        return _split_lines_by_budget(lines, config.max_chunk_chars)

    outline_ids = [heading_id for heading_id, _title in ir.outline]
    sections: list[list[str]] = []
    current: list[str] = []
    current_heading: str | None = None

    for line in lines:
        if line.startswith("[outline]"):
            break
        block_id = _line_block_id(line)
        if block_id in outline_ids and current:
            sections.append(current)
            current = []
        current.append(line)
        if block_id in outline_ids:
            current_heading = block_id

    if current:
        sections.append(current)

    if not sections:
        return _split_lines_by_budget(lines, config.max_chunk_chars)

    chunks: list[str] = []
    for section_lines in sections:
        section_text = "\n".join(section_lines)
        if len(section_text) <= config.max_chunk_chars:
            chunks.append(section_text)
            continue
        chunks.extend(_split_lines_by_budget(section_lines, config.max_chunk_chars))

    return [chunk for chunk in chunks if chunk.strip()]


def _split_lines_by_budget(lines: list[str], max_chars: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current and current_len + line_len > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))

    return chunks


def _line_block_id(line: str) -> str | None:
    stripped = line.lstrip()
    if not stripped.startswith("["):
        return None
    end = stripped.find("]")
    if end == -1:
        return None
    inner = stripped[1:end]
    return inner.split()[0] if inner else None
