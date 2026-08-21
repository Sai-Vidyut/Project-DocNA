"""Optional live AI provider integration test.

Skipped by default so the normal pytest suite stays offline. Run explicitly:

    DOCNA_LIVE_AI=1 uv run pytest tests/test_ai_integration.py -q
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from docna.ai.factory import create_ai_provider
from docna.ai.port import ChatMessage
from docna.config import Settings
from docna.detect.models import SemanticClassificationResponse


def _configured_settings() -> Settings | None:
    settings = Settings.from_env(storage_dir=Path.cwd() / "jobs")
    if settings.ai_provider == "mock" or not settings.provider_chain:
        return None
    return settings


pytestmark = pytest.mark.skipif(
    os.environ.get("DOCNA_LIVE_AI") != "1",
    reason="Set DOCNA_LIVE_AI=1 to run live provider integration test",
)


def test_live_provider_returns_structured_semantic_response() -> None:
    settings = _configured_settings()
    if settings is None:
        pytest.skip("No live AI provider chain configured")
    provider = create_ai_provider(settings)
    messages = [
        ChatMessage(
            role="user",
            content=(
                "Classify this block preview line:\n"
                "[blk_0001 paragraph] What is your name?"
            ),
        )
    ]
    response = provider.complete(messages, SemanticClassificationResponse)
    assert isinstance(response, SemanticClassificationResponse)
