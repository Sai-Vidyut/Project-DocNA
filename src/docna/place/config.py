"""Configurable placement policy thresholds and behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlacementConfig:
    """Policy knobs for deterministic placement planning."""

    confidence_threshold: float = 0.70
    overflow_ratio: float = 1.5
    ambiguous_space_behavior: str = "prefer_nearest_after"
    already_answered_behavior: str = "skip"
    low_confidence_behavior: str = "skip"

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")
        if self.overflow_ratio < 1.0:
            raise ValueError("overflow_ratio must be >= 1.0")
