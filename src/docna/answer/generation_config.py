"""Answer generation configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from docna.ai.metrics import ProviderMetrics


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    """Concurrency, batching, and retry policy for answer generation."""

    max_concurrency: int = 5
    max_retries: int = 2
    retry_backoff_seconds: float = 0.0
    batch_size: int = 5
    metrics: ProviderMetrics | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if self.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")

    @property
    def batching_enabled(self) -> bool:
        return self.batch_size > 1
