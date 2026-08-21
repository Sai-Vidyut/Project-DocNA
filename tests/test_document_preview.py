"""Tests for document preview builder."""

from __future__ import annotations

from docna.document_preview import build_document_preview
from docna.ir import Answer, Task
from docna.place.planner import plan_placements
from docna.review import ReviewReport, ReviewSummary, ReviewTaskEntry
from tests.placement_helpers import apply_ops, ensure_placement_fixture, parse_placement_fixture


def test_build_document_preview_marks_answer_regions(tmp_path) -> None:
    original = ensure_placement_fixture("empty_paragraph.docx")
    ir = parse_placement_fixture("empty_paragraph.docx")
    space = next(s for s in ir.answer_spaces if s.type == "empty_para")
    answer_text = "Five years of teaching experience."
    ops = plan_placements(
        ir,
        [
            Task(
                task_id="task_0001",
                kind="question",
                prompt_text="Describe your experience.",
                answer_space_id=space.space_id,
                confidence=0.9,
            )
        ],
        [Answer(task_id="task_0001", text=answer_text, confidence=0.9)],
    )
    output = apply_ops(original, ops, tmp_path)
    review = ReviewReport(
        job_id="job_test",
        status="completed",
        summary=ReviewSummary(
            questions_detected=1,
            answers_generated=1,
            items_skipped=0,
            items_needing_review=0,
        ),
        answered=[
            ReviewTaskEntry(
                task_id="task_0001",
                task_text="Describe your experience.",
                task_kind="question",
                answer_status="answered",
                answer_text=answer_text,
                answer_confidence=0.9,
                editable=True,
            )
        ],
    )
    preview = build_document_preview(job_id="job_test", output_path=output, review=review)
    answer_parts = [
        part for block in preview.blocks for part in block.parts if part.type == "answer"
    ]
    assert answer_parts
    assert answer_parts[0].value == answer_text
