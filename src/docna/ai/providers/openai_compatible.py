"""OpenAI-compatible chat completion provider (Cerebras, Groq, Hugging Face, OpenRouter)."""

from __future__ import annotations

import importlib
import json
from collections.abc import Sequence

from pydantic import BaseModel

from docna.ai.openai_provider import UsageStats
from docna.ai.port import ChatMessage
from docna.ai.structured import parse_json_response, with_schema_instruction


class OpenAICompatibleProvider:
    """Structured completion via OpenAI-compatible chat completions API."""

    def __init__(
        self,
        *,
        provider_name: str,
        api_key: str,
        model: str,
        base_url: str,
    ) -> None:
        try:
            openai_module = importlib.import_module("openai")
            OpenAI = openai_module.OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                f"openai package is required for provider {provider_name!r}. "
                "Install with: uv sync --extra openai"
            ) from exc

        self._provider_name = provider_name
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self.last_usage: UsageStats | None = None

    def complete(
        self,
        messages: Sequence[ChatMessage],
        response_schema: type[BaseModel],
    ) -> BaseModel:
        formatted = with_schema_instruction(list(messages), response_schema)
        payload = [{"role": message.role, "content": message.content} for message in formatted]
        schema = response_schema.model_json_schema()

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=payload,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_schema.__name__,
                        "schema": schema,
                        "strict": True,
                    },
                },
            )
        except Exception as exc:
            if not _should_retry_without_strict_schema(exc):
                raise
            response = self._client.chat.completions.create(
                model=self._model,
                messages=payload,
                response_format={"type": "json_object"},
            )

        self.last_usage = _extract_usage(response)
        text = _extract_message_text(response)
        return parse_json_response(text, response_schema)


def _should_retry_without_strict_schema(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "response_format",
            "json_schema",
            "strict",
            "unsupported",
            "not supported",
            "invalid parameter",
        )
    )


def _extract_message_text(response: object) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise RuntimeError("OpenAI-compatible response did not contain choices")
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None) if message else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenAI-compatible response did not contain message content")
    return content


def _extract_usage(response: object) -> UsageStats | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return UsageStats(
        input_tokens=getattr(usage, "prompt_tokens", None)
        or getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None)
        or getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )
