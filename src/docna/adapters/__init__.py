"""Format adapter package. Core code depends on ``FormatAdapter`` and the registry only."""

from docna.adapters.base import FormatAdapter, UnsupportedFormatError
from docna.adapters.registry import get_adapter, registered_formats

__all__ = [
    "FormatAdapter",
    "UnsupportedFormatError",
    "get_adapter",
    "registered_formats",
]
