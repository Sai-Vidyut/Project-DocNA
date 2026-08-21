"""Tests for structured JSON helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from docna.ai.port import ChatMessage
from docna.ai.structured import parse_json_response, with_schema_instruction


class _SampleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


def test_with_schema_instruction_appends_to_existing_system_message() -> None:
    messages = [
        ChatMessage(role="system", content="Base instruction"),
        ChatMessage(role="user", content="hello"),
    ]
    updated = with_schema_instruction(messages, _SampleResponse)
    assert updated[0].role == "system"
    assert "Base instruction" in updated[0].content
    assert "schema" in updated[0].content.lower()


def test_parse_json_response_strips_markdown_fence() -> None:
    response = parse_json_response('```json\n{"value": "ok"}\n```', _SampleResponse)
    assert response.value == "ok"


def test_parse_json_response_wraps_flat_answer_generation_payload() -> None:
    from docna.answer.models import AnswerGenerationResponse

    response = parse_json_response(
        '{"task_id": "task_0005", "text": "Jane Doe", "confidence": 0.9}',
        AnswerGenerationResponse,
    )
    assert response.answer.task_id == "task_0005"
    assert response.answer.text == "Jane Doe"
