"""Configurable limits for answer context packing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContextConfig:
    """Bounded, deterministic context selection."""

    max_nearby_blocks: int = 6
    max_context_chars: int = 8_000
    max_instruction_chars: int = 2_000
    nearby_radius: int = 3

    def __post_init__(self) -> None:
        if self.max_nearby_blocks < 1:
            raise ValueError("max_nearby_blocks must be at least 1")
        if self.max_context_chars < 500:
            raise ValueError("max_context_chars must be at least 500")
