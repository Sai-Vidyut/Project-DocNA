"""Tests for multi-provider primary/fallback AI configuration."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import BaseModel, ConfigDict

from docna.ai.fallback import FallbackAIProvider
from docna.ai.factory import create_ai_provider
from docna.ai.port import ChatMessage
from docna.ai.providers.spec import ProviderSpec
from docna.config import Settings


class _SampleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str = "ok"


class _FlakyProvider:
    def __init__(self, outcomes: list[object], *, name: str = "provider") -> None:
        self._outcomes = list(outcomes)
        self.calls = 0
        self.last_usage = None
        self.name = name

    def complete(
        self,
        messages: Sequence[ChatMessage],
        response_schema: type[BaseModel],
    ) -> BaseModel:
        self.calls += 1
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class AuthenticationError(Exception):
    pass


class APIStatusError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.status_code = 402


def test_fallback_provider_uses_second_provider_after_auth_failure() -> None:
    providers = [
        _FlakyProvider([AuthenticationError("bad key")], name="gemini"),
        _FlakyProvider([_SampleResponse(value="ok")], name="cerebras"),
    ]
    provider = FallbackAIProvider(providers)
    response = provider.complete(
        [ChatMessage(role="user", content="hello")],
        _SampleResponse,
    )

    assert response.value == "ok"
    assert providers[0].calls == 1
    assert providers[1].calls == 1


def test_fallback_provider_uses_next_provider_after_quota_exhaustion() -> None:
    providers = [
        _FlakyProvider(
            [APIStatusError("Error code: 402 - monthly included credits depleted")],
            name="huggingface",
        ),
        _FlakyProvider([_SampleResponse(value="ok")], name="openrouter"),
    ]
    provider = FallbackAIProvider(providers)
    response = provider.complete(
        [ChatMessage(role="user", content="hello")],
        _SampleResponse,
    )

    assert response.value == "ok"
    assert providers[0].calls == 1
    assert providers[1].calls == 1
    assert provider.last_provider == "openrouter"
    assert provider.last_fallback_attempt == 1


def test_fallback_provider_does_not_retry_non_fallback_errors() -> None:
    provider = _FlakyProvider([ValueError("invalid schema response")])
    fallback = FallbackAIProvider([provider, _FlakyProvider([_SampleResponse()])])
    with pytest.raises(ValueError, match="invalid schema response"):
        fallback.complete([ChatMessage(role="user", content="hello")], _SampleResponse)
    assert provider.calls == 1


def test_factory_creates_fallback_provider_for_configured_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built: list[ProviderSpec] = []

    def fake_build_provider(spec: ProviderSpec):
        built.append(spec)
        return _FlakyProvider([_SampleResponse()], name=spec.name)

    monkeypatch.setattr("docna.ai.factory.build_provider", fake_build_provider)

    settings = Settings(
        storage_dir="jobs",
        max_file_size=1024,
        ai_provider="gemini",
        max_concurrency=2,
        provider_chain=(
            ProviderSpec(name="gemini", api_key="key-1", model="gemini-3.6-flash"),
            ProviderSpec(name="cerebras", api_key="key-2", model="gpt-oss-120b"),
        ),
    )
    provider = create_ai_provider(settings)
    assert isinstance(provider, FallbackAIProvider)
    assert [spec.name for spec in built] == ["gemini", "cerebras"]


def test_factory_returns_single_provider_when_only_primary_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = _FlakyProvider([_SampleResponse()], name="gemini")
    monkeypatch.setattr("docna.ai.factory.build_provider", lambda spec: sentinel)

    settings = Settings(
        storage_dir="jobs",
        max_file_size=1024,
        ai_provider="gemini",
        max_concurrency=2,
        provider_chain=(
            ProviderSpec(name="gemini", api_key="key-1", model="gemini-3.6-flash"),
        ),
    )
    provider = create_ai_provider(settings)
    assert provider is sentinel


def test_factory_requires_configured_providers() -> None:
    settings = Settings(
        storage_dir="jobs",
        max_file_size=1024,
        ai_provider="gemini",
        max_concurrency=2,
        provider_chain=(),
    )
    with pytest.raises(ValueError, match="No AI providers are configured"):
        create_ai_provider(settings)
