"""Provider credential specification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    """Configured AI provider identity without exposing secrets in repr."""

    name: str
    api_key: str
    model: str
    base_url: str | None = None

    def __repr__(self) -> str:
        return f"ProviderSpec(name={self.name!r}, model={self.model!r}, base_url={self.base_url!r})"
