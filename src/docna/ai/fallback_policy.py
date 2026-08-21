"""Eligible failures for provider fallback."""

from __future__ import annotations

_FALLBACK_EXCEPTION_NAMES = frozenset(
    {
        "APIStatusError",
        "AuthenticationError",
        "PermissionDeniedError",
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
        "HTTPError",
        "URLError",
        "TimeoutError",
        "ConnectionError",
    }
)

_FALLBACK_MESSAGE_MARKERS = (
    "401",
    "402",
    "403",
    "429",
    "500",
    "502",
    "503",
    "504",
    "rate limit",
    "quota",
    "credits",
    "depleted",
    "payment required",
    "unauthorized",
    "authentication",
    "timeout",
    "temporarily unavailable",
    "service unavailable",
    "connection reset",
)


def should_fallback(exc: Exception) -> bool:
    if type(exc).__name__ in _FALLBACK_EXCEPTION_NAMES:
        return True
    if isinstance(exc, TimeoutError):
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _FALLBACK_MESSAGE_MARKERS)
