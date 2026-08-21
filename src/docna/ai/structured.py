"""Shared structured JSON completion helpers."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel

from docna.ai.port import ChatMessage


def schema_instruction(response_schema: type[BaseModel]) -> str:
    return (
        "Return valid JSON only, with no markdown fences, matching this schema:\n"
        f"{json.dumps(response_schema.model_json_schema())}"
    )


def with_schema_instruction(
    messages: list[ChatMessage],
    response_schema: type[BaseModel],
) -> list[ChatMessage]:
    instruction = schema_instruction(response_schema)
    if messages and messages[0].role == "system":
        return [
            ChatMessage(role="system", content=f"{messages[0].content}\n\n{instruction}"),
            *messages[1:],
        ]
    return [ChatMessage(role="system", content=instruction), *messages]


def parse_json_response(text: str, response_schema: type[BaseModel]) -> BaseModel:
    payload = json.loads(_extract_json_text(text))
    payload = _normalize_response_payload(payload, response_schema)
    return response_schema.model_validate(payload)


def _normalize_response_payload(
    payload: object,
    response_schema: type[BaseModel],
) -> object:
    if not isinstance(payload, dict):
        return payload
    if response_schema.__name__ != "AnswerGenerationResponse":
        return payload
    if "answer" in payload:
        return payload
    if {"task_id", "text"}.issubset(payload.keys()):
        return {"answer": payload}
    return payload


def _extract_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
        if match:
            return match.group(1)
    return stripped
