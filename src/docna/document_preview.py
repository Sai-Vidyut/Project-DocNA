"""Build a browser-friendly preview of the completed document."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from docna.adapters.docx import DocxAdapter
from docna.review import ReviewReport, ReviewTaskEntry


class PreviewPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["text", "answer"]
    value: str
    task_id: str | None = None
    editable: bool = False


class PreviewBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    kind: str
    parts: list[PreviewPart] = Field(default_factory=list)


class DocumentPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    filename: str
    blocks: list[PreviewBlock] = Field(default_factory=list)


def build_document_preview(
    *,
    job_id: str,
    output_path: Path,
    review: ReviewReport,
    filename: str | None = None,
) -> DocumentPreview:
    """Parse the completed DOCX and annotate answer regions for the review UI."""
    ir = DocxAdapter().parse(output_path)
    answer_entries = [
        entry
        for entry in review.answered
        if entry.answer_text and entry.answer_text.strip()
    ]
    blocks: list[PreviewBlock] = []
    for block in ir.blocks:
        text = block.text
        stripped = text.strip()
        if not stripped:
            continue
        whole_answer = _whole_block_answer(stripped, answer_entries)
        if whole_answer is not None:
            blocks.append(
                PreviewBlock(
                    block_id=block.block_id,
                    kind=block.kind,
                    parts=[
                        PreviewPart(
                            type="answer",
                            value=whole_answer.answer_text or stripped,
                            task_id=whole_answer.task_id,
                            editable=whole_answer.editable,
                        )
                    ],
                )
            )
            continue
        parts = _split_text_with_answers(text, answer_entries)
        blocks.append(
            PreviewBlock(
                block_id=block.block_id,
                kind=block.kind,
                parts=parts,
            )
        )
    return DocumentPreview(
        job_id=job_id,
        filename=filename or output_path.name,
        blocks=blocks,
    )


def _whole_block_answer(
    stripped_text: str,
    entries: list[ReviewTaskEntry],
) -> ReviewTaskEntry | None:
    for entry in entries:
        answer = (entry.answer_text or "").strip()
        if answer and stripped_text == answer:
            return entry
    return None


def _split_text_with_answers(
    text: str,
    entries: list[ReviewTaskEntry],
) -> list[PreviewPart]:
    matches: list[tuple[int, int, ReviewTaskEntry]] = []
    for entry in entries:
        answer = entry.answer_text or ""
        if not answer or answer not in text:
            continue
        start = 0
        while True:
            index = text.find(answer, start)
            if index < 0:
                break
            matches.append((index, index + len(answer), entry))
            start = index + len(answer)

    if not matches:
        return [PreviewPart(type="text", value=text)]

    matches.sort(key=lambda item: item[0])
    merged: list[tuple[int, int, ReviewTaskEntry]] = []
    for start, end, entry in matches:
        if merged and start < merged[-1][1]:
            continue
        merged.append((start, end, entry))

    parts: list[PreviewPart] = []
    cursor = 0
    for start, end, entry in merged:
        if start > cursor:
            parts.append(PreviewPart(type="text", value=text[cursor:start]))
        parts.append(
            PreviewPart(
                type="answer",
                value=text[start:end],
                task_id=entry.task_id,
                editable=entry.editable,
            )
        )
        cursor = end
    if cursor < len(text):
        parts.append(PreviewPart(type="text", value=text[cursor:]))
    return parts
