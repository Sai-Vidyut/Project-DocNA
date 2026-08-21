"""Structural detection unit tests."""

from __future__ import annotations

from docna.detect.structural import detect_structural
from tests.detect_helpers import parse_fixture


def test_structural_finds_numbered_questions() -> None:
    ir = parse_fixture("numbered_questions.docx")
    result = detect_structural(ir)
    assert result.candidates
    assert any("question_mark" in c.signals or "numbered_item" in c.signals for c in result.candidates)


def test_structural_finds_sub_question_candidates() -> None:
    ir = parse_fixture("detection_mixed.docx")
    result = detect_structural(ir)
    sub_items = [c for c in result.candidates if c.provisional_kind == "sub_question"]
    assert sub_items
    assert any("letter_subitem" in c.signals for c in sub_items)


def test_structural_detects_instructions() -> None:
    ir = parse_fixture("mixed_document.docx")
    result = detect_structural(ir)
    assert any("complete all" in i.prompt_text.lower() for i in result.instruction_candidates)


def test_structural_binds_blank_run_spaces() -> None:
    ir = parse_fixture("blank_answers.docx")
    result = detect_structural(ir)
    assert any(c.suggested_answer_space_id for c in result.candidates)


def test_structural_binds_empty_table_cells() -> None:
    ir = parse_fixture("tables.docx")
    result = detect_structural(ir)
    table_candidates = [c for c in result.candidates if c.provisional_kind == "table_item"]
    assert table_candidates or any(c.suggested_answer_space_id for c in result.candidates)


def test_structural_does_not_import_llm_stack() -> None:
    import ast
    from pathlib import Path

    source = Path("src/docna/detect/structural.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "docna.ai" in node.module:
            raise AssertionError("structural.py must not import AI modules")
