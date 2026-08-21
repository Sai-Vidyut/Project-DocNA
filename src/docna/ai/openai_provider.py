"""OpenAI structured-output provider behind the AIProvider port."""

from __future__ import annotations

import importlib
import json
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import BaseModel

from docna.ai.port import ChatMessage


@dataclass(slots=True)
class UsageStats:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class OpenAIProvider:
    """Structured completion using the OpenAI Responses API."""

    def __init__(self, *, api_key: str, model: str) -> None:
        try:
            openai_module = importlib.import_module("openai")
            OpenAI = openai_module.OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "openai package is required for DOCNA_AI_PROVIDER=openai"
            ) from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self.last_usage: UsageStats | None = None

    def complete(
        self,
        messages: Sequence[ChatMessage],
        response_schema: type[BaseModel],
    ) -> BaseModel:
        schema = response_schema.model_json_schema()
        response = self._client.responses.create(
            model=self._model,
            input=[{"role": message.role, "content": message.content} for message in messages],
            text={
                "format": {
                    "type": "json_schema",
                    "name": response_schema.__name__,
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        self.last_usage = _extract_usage(response)
        text = _extract_response_text(response)
        payload = json.loads(text)
        return response_schema.model_validate(payload)


def _extract_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output = getattr(response, "output", None)
    if not output:
        raise RuntimeError("OpenAI response did not contain output text")

    chunks: list[str] = []
    for item in output:
        content = getattr(item, "content", None)
        if not content:
            continue
        for part in content:
            text = getattr(part, "text", None)
            if isinstance(text, str):
                chunks.append(text)
    combined = "".join(chunks).strip()
    if not combined:
        raise RuntimeError("OpenAI response did not contain output text")
    return combined


def _extract_usage(response: object) -> UsageStats | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return UsageStats(
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )
