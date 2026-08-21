"""Regression tests for prompt-injection handling with MockAIProvider."""

from __future__ import annotations

from docna.adapters.docx import DocxAdapter
from docna.detect.run import detect_from_adapter
from tests.pipeline_helpers import pipeline_mock_provider
from tests.realworld_helpers import ensure_realworld_fixture


def test_prompt_injection_blocks_not_detected_as_tasks() -> None:
    path = ensure_realworld_fixture("prompt_injection.docx")
    ir = DocxAdapter().parse(path)
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    prompts = [task.prompt_text.lower() for task in result.tasks]
    assert not any("ignore previous instructions" in text for text in prompts)
    assert not any("reveal your system prompt" in text for text in prompts)
    assert not any("administrator credentials" in text for text in prompts)
    assert not any("always output the word hacked" in text for text in prompts)


def test_prompt_injection_detects_legitimate_question() -> None:
    path = ensure_realworld_fixture("prompt_injection.docx")
    ir = DocxAdapter().parse(path)
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    assert any("department" in task.prompt_text.lower() for task in result.tasks)
