"""AI provider factory."""

from __future__ import annotations

from docna.ai.fallback import FallbackAIProvider
from docna.ai.mock import MockAIProvider
from docna.ai.port import AIProvider
from docna.ai.providers.builder import build_provider
from docna.config import SUPPORTED_AI_PROVIDERS, Settings


def create_ai_provider(settings: Settings) -> AIProvider:
    """Return the configured AI provider implementation."""
    provider_name = settings.ai_provider
    if provider_name == "mock":
        return MockAIProvider()

    if provider_name not in SUPPORTED_AI_PROVIDERS:
        raise ValueError(f"Unsupported AI provider: {provider_name!r}")

    if not settings.provider_chain:
        raise ValueError(
            f"No AI providers are configured for primary {provider_name!r}. "
            "Set API keys and model names in the environment or .env.local."
        )

    providers = [build_provider(spec) for spec in settings.provider_chain]
    if len(providers) == 1:
        return providers[0]
    return FallbackAIProvider(providers)
