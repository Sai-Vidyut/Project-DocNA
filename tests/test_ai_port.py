"""AI provider port is a contract only in Phase 1."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from docna.ai.port import AIProvider, ChatMessage

PORT_PATH = Path(__file__).resolve().parents[1] / "src" / "docna" / "ai" / "port.py"


def test_ai_provider_is_a_protocol_with_structured_complete() -> None:
    assert getattr(AIProvider, "_is_protocol", False) is True
    signature = inspect.signature(AIProvider.complete)
    assert list(signature.parameters) == ["self", "messages", "response_schema"]


def test_chat_message_rejects_unknown_role() -> None:
    with pytest.raises(ValidationError):
        ChatMessage(role="tool", content="hi")  # type: ignore[arg-type]


def test_ai_port_does_not_import_a_vendor_sdk() -> None:
    tree = ast.parse(PORT_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint({"openai", "anthropic", "langchain"})
