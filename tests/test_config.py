"""Configuration and .env.local loading tests."""

from __future__ import annotations

import os

import pytest

from docna.config import Settings, load_dotenv_local, parse_provider_chain, parse_provider_spec


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "AI_PROVIDER",
        "AI_FALLBACK_PROVIDERS",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "CEREBRAS_API_KEY",
        "CEREBRAS_MODEL",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "HF_TOKEN",
        "HF_MODEL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_load_dotenv_local_does_not_override_existing_env(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "GEMINI_API_KEY=from-file\nAI_PROVIDER=gemini\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GEMINI_API_KEY", "existing")
    load_dotenv_local(env_file)
    assert os.environ["GEMINI_API_KEY"] == "existing"


def test_load_dotenv_local_populates_missing_env(tmp_path) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "\n".join(
            [
                "AI_PROVIDER=gemini",
                "GEMINI_API_KEY=gemini-key",
                "GEMINI_MODEL=gemini-3.6-flash",
                "CEREBRAS_API_KEY=cerebras-key",
                "CEREBRAS_MODEL=gpt-oss-120b",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    load_dotenv_local(env_file)
    settings = Settings.from_env(dotenv_path=env_file)
    assert settings.ai_provider == "gemini"
    assert [spec.name for spec in settings.provider_chain] == ["gemini", "cerebras"]


def test_parse_provider_chain_orders_primary_then_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    chain = parse_provider_chain("gemini")
    assert [spec.name for spec in chain] == ["gemini", "groq", "openrouter"]


def test_parse_provider_spec_requires_key_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    assert parse_provider_spec("gemini") is None


def test_settings_supports_ai_provider_alias_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
    settings = Settings.from_env()
    assert settings.ai_provider == "gemini"
    assert settings.provider_chain[0].name == "gemini"


def test_parse_fallback_order_reads_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_FALLBACK_PROVIDERS", "openrouter,groq")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
    monkeypatch.setenv("GROQ_API_KEY", "groq-key")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    chain = parse_provider_chain("gemini")
    assert [spec.name for spec in chain] == ["gemini", "openrouter", "groq"]


def test_docna_env_vars_take_precedence_over_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCNA_AI_PROVIDER", "mock")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    settings = Settings.from_env()
    assert settings.ai_provider == "mock"
