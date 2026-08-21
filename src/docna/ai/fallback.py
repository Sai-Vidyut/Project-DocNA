"""Primary provider with ordered multi-provider fallback."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from docna.ai.fallback_policy import should_fallback
from docna.ai.openai_provider import UsageStats
from docna.ai.port import ChatMessage


class FallbackAIProvider:
    """Try configured providers in order until one succeeds."""

    def __init__(self, providers: Sequence[object]) -> None:
        if not providers:
            raise ValueError("At least one AI provider is required")
        self._providers = list(providers)
        self.last_usage: UsageStats | None = None
        self.last_provider: str | None = None
        self.last_model: str | None = None
        self.last_fallback_attempt: int = 0

    def complete(
        self,
        messages: Sequence[ChatMessage],
        response_schema: type[BaseModel],
    ) -> BaseModel:
        last_error: Exception | None = None

        for index, provider in enumerate(self._providers):
            try:
                response = provider.complete(messages, response_schema)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if index < len(self._providers) - 1 and should_fallback(exc):
                    continue
                raise

            self.last_usage = getattr(provider, "last_usage", None)
            self.last_fallback_attempt = index
            self.last_provider = (
                getattr(provider, "_provider_name", None)
                or getattr(provider, "name", None)
                or type(provider).__name__
            )
            self.last_model = getattr(provider, "_model", None)
            return response

        if last_error is not None:
            raise last_error
        raise RuntimeError("No AI providers configured")
