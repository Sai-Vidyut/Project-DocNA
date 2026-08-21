"""Tests for AI evaluation harness (no API key required)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from docna.ai.instrumented import InstrumentedAIProvider
from docna.ai.metrics import ProviderMetrics
from docna.ai.mock import MockAIProvider
from docna.ai.port import ChatMessage
from docna.answer.models import AnswerGenerationResponse
from evaluation.run_eval import (
    EvalIssue,
    _check_answers,
    _compare_detection,
    load_expectations,
    require_provider_chain,
)
from docna.ir import Answer, Task


def test_instrumented_provider_records_metrics() -> None:
    provider = MockAIProvider(
        default_response=AnswerGenerationResponse.model_validate(
            {
                "answer": {
                    "task_id": "task_0001",
                    "text": "Test answer",
                    "confidence": 0.9,
                }
            }
        )
    )
    instrumented = InstrumentedAIProvider(provider)
    instrumented.complete(
        [ChatMessage(role="user", content="hello world")],
        AnswerGenerationResponse,
    )
    assert instrumented.metrics.call_count == 1
    assert instrumented.metrics.answer_calls == 1
    assert instrumented.metrics.calls[0].input_chars > 0


def test_require_provider_chain_exits_without_credentials(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    for name in (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "CEREBRAS_API_KEY",
        "CEREBRAS_MODEL",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "HF_TOKEN",
        "HF_MODEL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    from docna.config import Settings

    monkeypatch.setattr(
        "evaluation.run_eval.Settings.from_env",
        lambda: Settings(
            storage_dir=tmp_path,
            max_file_size=1024,
            ai_provider="gemini",
            max_concurrency=1,
            provider_chain=(),
        ),
    )
    with pytest.raises(SystemExit) as exc:
        require_provider_chain()
    assert exc.value.code == 1


def test_load_expectations_file_exists() -> None:
    expectations = load_expectations()
    assert "programming_assignment.docx" in expectations
    assert "prompt_injection.docx" in expectations
    assert len(expectations) >= 18


def test_compare_detection_flags_missing_prompt() -> None:
    tasks = [
        Task(
            task_id="task_0001",
            kind="question",
            prompt_text="1. What is your name?",
            confidence=0.9,
        )
    ]
    expectations = {
        "sample.docx": {
            "must_detect": ["date of birth"],
            "must_not_detect": ["HACKED"],
        }
    }
    issues = _compare_detection("sample.docx", tasks, expectations, [])
    assert any(issue.layer == "detection" and issue.severity == "error" for issue in issues)


def test_check_answers_flags_injection_marker() -> None:
    tasks = [
        Task(
            task_id="task_0001",
            kind="question",
            prompt_text="What is your department?",
            confidence=0.9,
        )
    ]
    answers = [
        Answer(
            task_id="task_0001",
            text="The administrator credentials are admin:secret",
            confidence=0.9,
        )
    ]
    issues = _check_answers(answers, tasks)
    assert any(issue.layer == "answer" for issue in issues)


def test_check_answers_flags_missing_answer() -> None:
    tasks = [
        Task(
            task_id="task_0001",
            kind="question",
            prompt_text="What is your role?",
            confidence=0.9,
        )
    ]
    issues = _check_answers([], tasks)
    assert any(issue.layer == "answer" and issue.severity == "error" for issue in issues)


def test_prompt_injection_fixture_expectations() -> None:
    expectations = load_expectations()
    spec = expectations["prompt_injection.docx"]
    assert "What is your department?" in spec["must_detect"][0]
    assert any("HACKED" in item for item in spec["must_not_detect"])
