"""Instrumented wrapper around any AIProvider implementation."""

from __future__ import annotations

import time
from collections.abc import Sequence

from pydantic import BaseModel

from docna.ai.metrics import CallRecord, ProviderMetrics
from docna.ai.port import ChatMessage


class InstrumentedAIProvider:
    """Wraps a provider to collect per-call latency and token metrics."""

    def __init__(self, provider: object, *, metrics: ProviderMetrics | None = None) -> None:
        self._provider = provider
        self.metrics = metrics or ProviderMetrics()

    def complete(
        self,
        messages: Sequence[ChatMessage],
        response_schema: type[BaseModel],
    ) -> BaseModel:
        input_chars = sum(len(message.content) for message in messages)
        started = time.perf_counter()
        response = self._provider.complete(messages, response_schema)
        elapsed_ms = (time.perf_counter() - started) * 1000
        output_chars = len(response.model_dump_json())

        usage = getattr(self._provider, "last_usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage else None
        output_tokens = getattr(usage, "output_tokens", None) if usage else None
        total_tokens = getattr(usage, "total_tokens", None) if usage else None
        provider_name = (
            getattr(self._provider, "last_provider", None)
            or getattr(self._provider, "_provider_name", None)
            or getattr(self._provider, "name", None)
        )
        model_name = getattr(self._provider, "last_model", None) or getattr(
            self._provider, "_model", None
        )
        fallback_attempt = getattr(self._provider, "last_fallback_attempt", None)

        self.metrics.calls.append(
            CallRecord(
                call_type=_call_type_for_schema(response_schema),
                schema_name=response_schema.__name__,
                elapsed_ms=elapsed_ms,
                input_chars=input_chars,
                output_chars=output_chars,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                provider=provider_name,
                model=model_name,
                fallback_attempt=fallback_attempt,
                tasks_in_batch=_tasks_in_batch_for_response(response_schema, response),
            )
        )
        return response


def _call_type_for_schema(response_schema: type[BaseModel]) -> str:
    name = response_schema.__name__
    if name == "SemanticClassificationResponse":
        return "semantic"
    if name == "BatchAnswerGenerationResponse":
        return "answer_batch"
    if name == "AnswerGenerationResponse":
        return "answer"
    return "other"


def _tasks_in_batch_for_response(
    response_schema: type[BaseModel],
    response: BaseModel,
) -> int | None:
    if response_schema.__name__ != "BatchAnswerGenerationResponse":
        return None
    answers = getattr(response, "answers", None)
    if answers is None:
        return None
    return len(answers)
