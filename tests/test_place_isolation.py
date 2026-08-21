"""Prove placement modules stay format-agnostic."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "docna" / "place"


def test_planner_does_not_inspect_locator_payload() -> None:
    forbidden = ('payload["', "payload.get(", "payload['", "body_index", "xpath")
    hits: list[str] = []
    for path in SRC.rglob("*.py"):
        if path.name == "config.py":
            continue
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in source:
                hits.append(f"{path.name}: {token}")
    assert hits == []


def test_planner_does_not_import_docx_adapter_internals() -> None:
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "docna.adapters.docx" in node.module:
                    violations.append(f"{path.name} imports {node.module}")
    assert violations == []
