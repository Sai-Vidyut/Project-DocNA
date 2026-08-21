"""Merge logic unit tests."""

from __future__ import annotations

from docna.detect.config import DetectionConfig
from docna.detect.merge import merge_detections
from docna.detect.models import (
    SemanticClassificationItem,
    SemanticDetectionResult,
    StructuralCandidate,
    StructuralDetectionResult,
)
from docna.detect.structural import detect_structural
from tests.detect_helpers import parse_fixture, preview_fixture, rule_based_mock_provider
from docna.detect.run import detect_document_tasks


def test_merge_creates_parent_child_tasks() -> None:
    ir = parse_fixture("detection_mixed.docx")
    structural = detect_structural(ir)
    semantic = SemanticDetectionResult(
        classifications=[
            SemanticClassificationItem(
                block_id=c.block_id,
                kind="sub_question" if "a)" in c.prompt_text or "b)" in c.prompt_text else "question",
                confidence=0.92,
                reason="test",
            )
            for c in structural.candidates
            if "inheritance" in c.prompt_text or "polymorphism" in c.prompt_text
        ]
    )
    result = merge_detections(ir, structural, semantic)
    sub_tasks = [t for t in result.tasks if t.kind == "sub_question"]
    assert sub_tasks
    assert any(t.parent_task_id for t in sub_tasks)


def test_merge_drops_instructions_from_answerable_queue() -> None:
    ir, preview = preview_fixture("detection_mixed.docx")
    result = detect_document_tasks(ir, preview, rule_based_mock_provider())
    instructions = [t for t in result.tasks if t.kind == "instruction"]
    answerable = result.answerable_tasks
    assert instructions
    assert all(task.kind != "instruction" for task in answerable)


def test_merge_marks_already_answered() -> None:
    ir = parse_fixture("numbered_questions.docx")
    structural = detect_structural(ir)
    candidate = structural.candidates[0]
    semantic = SemanticDetectionResult(
        classifications=[
            SemanticClassificationItem(
                block_id=candidate.block_id,
                kind="already_answered",
                confidence=0.95,
                reason="answered in document",
            )
        ]
    )
    result = merge_detections(ir, structural, semantic)
    already = [t for t in result.tasks if t.skip_reason == "already_answered"]
    assert already


def test_merge_low_confidence_not_answerable() -> None:
    ir = parse_fixture("numbered_questions.docx")
    structural = detect_structural(ir)
    semantic = SemanticDetectionResult(
        classifications=[
            SemanticClassificationItem(
                block_id=c.block_id,
                kind="question",
                confidence=0.55,
                reason="uncertain",
            )
            for c in structural.candidates
        ]
    )
    config = DetectionConfig(review_threshold=0.70, safe_threshold=0.90)
    result = merge_detections(ir, structural, semantic, config=config)
    assert all(t.skip_reason == "low_confidence" for t in result.answerable_tasks) or not result.answerable_tasks
    assert any("low_confidence" in w for w in result.warnings)


def test_merge_attaches_answer_spaces() -> None:
    ir, preview = preview_fixture("blank_answers.docx")
    result = detect_document_tasks(ir, preview, rule_based_mock_provider())
    assert any(task.answer_space_id for task in result.tasks)
