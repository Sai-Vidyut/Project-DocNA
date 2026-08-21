"""Prove core modules do not depend on DOCX implementation details."""

from __future__ import annotations

import ast
from pathlib import Path

CORE_RELATIVE_PATHS = (
    "ir.py",
    "pipeline.py",
    "detect",
    "answer",
    "place",
    "ai",
    "storage",
)

FORBIDDEN_TOP_LEVEL_IMPORTS = {
    "docx",
    "lxml",
    "zipfile",
    "openai",
    "langchain",
    "mammoth",
    "unstructured",
}

FORBIDDEN_MODULE_PREFIXES = (
    "docna.adapters.docx",
    "docx",
    "lxml",
)

SRC = Path(__file__).resolve().parents[1] / "src" / "docna"


def _core_python_files() -> list[Path]:
    files: list[Path] = []
    for relative in CORE_RELATIVE_PATHS:
        path = SRC / relative
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        else:
            files.append(path)
    return files


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_core_modules_do_not_import_docx_stack() -> None:
    violations: list[str] = []
    for path in _core_python_files():
        for name in _imported_names(path):
            top = name.split(".", 1)[0]
            if top in FORBIDDEN_TOP_LEVEL_IMPORTS:
                violations.append(f"{path.relative_to(SRC.parent)} imports {name}")
            if any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_MODULE_PREFIXES):
                violations.append(f"{path.relative_to(SRC.parent)} imports {name}")
    assert violations == []


def test_core_modules_do_not_import_format_writer_apis() -> None:
    """Core may mention formats in docs; it must not import writer stacks."""
    violations: list[str] = []
    for path in _core_python_files():
        for name in _imported_names(path):
            top = name.split(".", 1)[0]
            if top in {"docx", "lxml", "zipfile"}:
                violations.append(f"{path.name} imports {name}")
    assert violations == []
