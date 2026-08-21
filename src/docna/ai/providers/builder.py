"""Build concrete AIProvider instances from configuration specs."""

from __future__ import annotations

from docna.ai.openai_provider import OpenAIProvider
from docna.ai.port import AIProvider
from docna.ai.providers.gemini import GeminiProvider
from docna.ai.providers.openai_compatible import OpenAICompatibleProvider
from docna.ai.providers.spec import ProviderSpec

_OPENAI_COMPATIBLE_DEFAULTS: dict[str, str] = {
    "cerebras": "https://api.cerebras.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "huggingface": "https://router.huggingface.co/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


def build_provider(spec: ProviderSpec) -> AIProvider:
    """Instantiate a provider implementation for the given spec."""
    name = spec.name.lower()
    if name == "openai":
        return OpenAIProvider(api_key=spec.api_key, model=spec.model)
    if name == "gemini":
        return GeminiProvider(api_key=spec.api_key, model=spec.model)
    if name in _OPENAI_COMPATIBLE_DEFAULTS:
        base_url = spec.base_url or _OPENAI_COMPATIBLE_DEFAULTS[name]
        return OpenAICompatibleProvider(
            provider_name=name,
            api_key=spec.api_key,
            model=spec.model,
            base_url=base_url,
        )
    raise ValueError(f"Unsupported AI provider: {spec.name!r}")
