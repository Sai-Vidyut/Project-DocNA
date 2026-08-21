"""Google Gemini structured-output provider."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence

from pydantic import BaseModel

from docna.ai.openai_provider import UsageStats
from docna.ai.port import ChatMessage
from docna.ai.structured import parse_json_response, with_schema_instruction

_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider:
    """Structured completion using the Gemini generateContent API."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self.last_usage: UsageStats | None = None

    def complete(
        self,
        messages: Sequence[ChatMessage],
        response_schema: type[BaseModel],
    ) -> BaseModel:
        formatted = with_schema_instruction(list(messages), response_schema)
        system_parts: list[str] = []
        contents: list[dict] = []

        for message in formatted:
            if message.role == "system":
                system_parts.append(message.content)
                continue
            role = "user" if message.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": message.content}]})

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Respond as requested."}]}]

        body: dict = {
            "contents": contents,
            "generationConfig": {
                "responseMimeType": "application/json",
            },
        }
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        url = f"{_GEMINI_API_BASE}/models/{self._model}:generateContent"
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API error {exc.code}: {detail}") from exc

        self.last_usage = _extract_usage(payload)
        text = _extract_text(payload)
        return parse_json_response(text, response_schema)


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini response did not contain candidates")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    chunks = [part.get("text", "") for part in parts if isinstance(part.get("text"), str)]
    combined = "".join(chunks).strip()
    if not combined:
        raise RuntimeError("Gemini response did not contain text")
    return combined


def _extract_usage(payload: dict) -> UsageStats | None:
    usage = payload.get("usageMetadata")
    if not isinstance(usage, dict):
        return None
    return UsageStats(
        input_tokens=usage.get("promptTokenCount"),
        output_tokens=usage.get("candidatesTokenCount"),
        total_tokens=usage.get("totalTokenCount"),
    )
