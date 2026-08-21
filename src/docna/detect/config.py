"""Configurable thresholds and limits for document detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DetectionConfig:
    """Confidence and chunking policy for hybrid detection."""

    safe_threshold: float = 0.90
    review_threshold: float = 0.70
    max_chunk_chars: int = 12_000
    context_neighbor_blocks: int = 2

    def __post_init__(self) -> None:
        if not 0.0 <= self.review_threshold <= 1.0:
            raise ValueError("review_threshold must be between 0 and 1")
        if not 0.0 <= self.safe_threshold <= 1.0:
            raise ValueError("safe_threshold must be between 0 and 1")
        if self.review_threshold > self.safe_threshold:
            raise ValueError("review_threshold must be <= safe_threshold")
        if self.max_chunk_chars < 500:
            raise ValueError("max_chunk_chars must be at least 500")
