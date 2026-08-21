"""End-to-end detection integration tests without a real LLM."""

from __future__ import annotations

import hashlib

import pytest

from docna.adapters.docx import DocxAdapter
from docna.detect.run import detect_from_adapter
from tests.detect_helpers import ensure_fixture, parse_fixture, rule_based_mock_provider


@pytest.fixture(scope="module")
def detection_ir():
    return parse_fixture("detection_mixed.docx")


def test_detection_fixture_distinguishes_task_types(detection_ir) -> None:
    adapter = DocxAdapter()
    preview = adapter.preview_text(detection_ir)
    result = detect_from_adapter(detection_ir, adapter, rule_based_mock_provider())

    questions = [
        t
        for t in result.tasks
        if t.kind == "question" and t.skip_reason is None and "?" in t.prompt_text
    ]
    sub_questions = [t for t in result.tasks if t.kind == "sub_question"]
    instructions = [t for t in result.tasks if t.kind == "instruction"]

    assert questions
    assert sub_questions
    assert instructions
    assert any("complete all fields" in t.prompt_text.lower() for t in instructions)
    assert any("inheritance" in t.prompt_text.lower() for t in sub_questions)
    prompts = [t.prompt_text.lower() for t in result.tasks]
    assert not any("encapsulation is the bundling" in text for text in prompts)
    assert not any(text.strip() == "answer: manager" for text in prompts)


def test_detection_does_not_mutate_source_docx() -> None:
    path = ensure_fixture("detection_mixed.docx")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    ir = parse_fixture("detection_mixed.docx")
    detect_from_adapter(ir, DocxAdapter(), rule_based_mock_provider())
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == after


def test_detection_preview_has_no_locator_payloads(detection_ir) -> None:
    preview = DocxAdapter().preview_text(detection_ir)
    assert "body_index" not in preview
    assert "xpath" not in preview
    assert "document.xml" not in preview
