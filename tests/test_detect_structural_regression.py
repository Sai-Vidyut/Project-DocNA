"""Structural detection regression tests from real-world validation."""

from __future__ import annotations

from docna.detect.structural import detect_structural
from tests.detect_helpers import parse_fixture
from tests.realworld_helpers import ensure_realworld_fixture
from docna.adapters.docx import DocxAdapter


def test_structural_detects_numbered_imperatives_without_question_mark() -> None:
    path = ensure_realworld_fixture("programming_assignment.docx")
    ir = DocxAdapter().parse(path)
    result = detect_structural(ir)
    prompts = [candidate.prompt_text for candidate in result.candidates]
    assert any("Implement a function" in text for text in prompts)
    assert any("Bonus:" in text for text in prompts)


def test_structural_detects_exercise_items() -> None:
    path = ensure_realworld_fixture("examples_not_answered.docx")
    ir = DocxAdapter().parse(path)
    result = detect_structural(ir)
    assert any("exercise_item" in c.signals for c in result.candidates)
    assert len(result.candidates) == 3


def test_structural_skips_example_question_lines() -> None:
    path = ensure_realworld_fixture("programming_assignment.docx")
    ir = DocxAdapter().parse(path)
    result = detect_structural(ir)
    assert not any(c.prompt_text.startswith("Question:") for c in result.candidates)


def test_structural_binds_empty_paragraphs_in_order() -> None:
    path = ensure_realworld_fixture("blank_lines.docx")
    ir = DocxAdapter().parse(path)
    result = detect_structural(ir)
    questions = [c for c in result.candidates if c.provisional_kind == "question"]
    space_ids = [c.suggested_answer_space_id for c in questions]
    assert len(set(space_ids)) == len(space_ids)
    assert all(space_id is not None for space_id in space_ids)


def test_structural_still_finds_numbered_questions_in_existing_fixtures() -> None:
    ir = parse_fixture("numbered_questions.docx")
    result = detect_structural(ir)
    assert result.candidates
    assert any("question_mark" in c.signals or "numbered_item" in c.signals for c in result.candidates)


def test_structural_detects_lettered_subquestions_in_numbered_subquestions_fixture() -> None:
    path = ensure_realworld_fixture("numbered_subquestions.docx")
    ir = DocxAdapter().parse(path)
    result = detect_structural(ir)
    sub_questions = [
        candidate
        for candidate in result.candidates
        if candidate.provisional_kind == "sub_question"
    ]
    assert len(sub_questions) >= 3
    labels = {candidate.prompt_text.split()[0] for candidate in sub_questions}
    assert {"a)", "b)", "c)"}.issubset(labels)
    parent_ids = {candidate.parent_block_id for candidate in sub_questions}
    assert any(parent_id is not None for parent_id in parent_ids)
