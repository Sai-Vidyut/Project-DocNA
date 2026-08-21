"""Metrics collected during AI provider calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class CallRecord:
    """One structured completion call."""

    call_type: str
    schema_name: str
    elapsed_ms: float
    input_chars: int
    output_chars: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    provider: str | None = None
    model: str | None = None
    fallback_attempt: int | None = None
    tasks_in_batch: int | None = None
    retry_attempt: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class ProviderMetrics:
    """Aggregated metrics for an evaluation run."""

    calls: list[CallRecord] = field(default_factory=list)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    @property
    def semantic_calls(self) -> int:
        return sum(1 for call in self.calls if call.call_type == "semantic")

    @property
    def answer_calls(self) -> int:
        return sum(1 for call in self.calls if call.call_type == "answer")

    @property
    def answer_batch_calls(self) -> int:
        return sum(1 for call in self.calls if call.call_type == "answer_batch")

    @property
    def total_ai_calls(self) -> int:
        return self.call_count

    @property
    def retry_count(self) -> int:
        return sum(1 for call in self.calls if (call.retry_attempt or 0) > 0)

    @property
    def batched_task_count(self) -> int:
        return sum(call.tasks_in_batch or 0 for call in self.calls if call.call_type == "answer_batch")

    @property
    def total_elapsed_ms(self) -> float:
        return sum(call.elapsed_ms for call in self.calls)

    @property
    def estimated_input_tokens(self) -> int:
        if all(call.input_tokens is not None for call in self.calls):
            return sum(call.input_tokens or 0 for call in self.calls)
        return sum(max(1, call.input_chars // 4) for call in self.calls)

    @property
    def estimated_output_tokens(self) -> int:
        if all(call.output_tokens is not None for call in self.calls):
            return sum(call.output_tokens or 0 for call in self.calls)
        return sum(max(1, call.output_chars // 4) for call in self.calls)

    def to_dict(self) -> dict:
        return {
            "call_count": self.call_count,
            "total_ai_calls": self.total_ai_calls,
            "semantic_calls": self.semantic_calls,
            "answer_calls": self.answer_calls,
            "answer_batch_calls": self.answer_batch_calls,
            "batched_task_count": self.batched_task_count,
            "retry_count": self.retry_count,
            "total_elapsed_ms": round(self.total_elapsed_ms, 2),
            "total_pipeline_ai_ms": round(self.total_elapsed_ms, 2),
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "calls": [
                {
                    "call_type": call.call_type,
                    "schema_name": call.schema_name,
                    "elapsed_ms": round(call.elapsed_ms, 2),
                    "input_chars": call.input_chars,
                    "output_chars": call.output_chars,
                    "input_tokens": call.input_tokens,
                    "output_tokens": call.output_tokens,
                    "total_tokens": call.total_tokens,
                    "provider": call.provider,
                    "model": call.model,
                    "fallback_attempt": call.fallback_attempt,
                    "tasks_in_batch": call.tasks_in_batch,
                    "retry_attempt": call.retry_attempt,
                    "timestamp": call.timestamp,
                }
                for call in self.calls
            ],
        }
