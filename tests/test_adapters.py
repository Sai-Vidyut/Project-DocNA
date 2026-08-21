"""Adapter contract, registry, and stub tests."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from docna.adapters.base import FormatAdapter, UnsupportedFormatError
from docna.adapters.docx import DocxAdapter
from docna.adapters.docx.locators import DOCX_ADAPTER_NAME, DocxLocatorData, make_docx_locator
from docna.adapters.md import MarkdownAdapter
from docna.adapters.pdf import PdfAdapter
from docna.adapters.pptx import PptxAdapter
from docna.adapters.registry import get_adapter, registered_formats
from docna.adapters.txt import TxtAdapter
from docna.ir import SOURCE_FORMATS, PlacementOp
from tests.helpers import sample_block, sample_document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = PROJECT_ROOT / "src" / "docna" / "adapters" / "registry.py"
BASE_PATH = PROJECT_ROOT / "src" / "docna" / "adapters" / "base.py"

ADAPTER_TYPES = {
    "docx": DocxAdapter,
    "pdf": PdfAdapter,
    "txt": TxtAdapter,
    "md": MarkdownAdapter,
    "pptx": PptxAdapter,
}


def test_format_adapter_exposes_only_format_agnostic_operations() -> None:
    assert FormatAdapter.__abstractmethods__ == frozenset({"parse", "apply"})
    parse_params = list(inspect.signature(FormatAdapter.parse).parameters)
    apply_params = list(inspect.signature(FormatAdapter.apply).parameters)
    preview_params = list(inspect.signature(FormatAdapter.preview_text).parameters)
    assert parse_params == ["self", "path"]
    assert apply_params == ["self", "source_copy", "ops"]
    assert preview_params == ["self", "ir"]

    source = ast.parse(BASE_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(source):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert imported.isdisjoint({"docx", "lxml", "zipfile", "openai"})


def test_preview_text_is_format_agnostic() -> None:
    ir = sample_document(sample_block("blk_0001", "Full name?"))
    preview = DocxAdapter().preview_text(ir)
    assert "[blk_0001 paragraph] Full name?" in preview
    assert "document.xml" not in preview
    assert "w:p" not in preview


def test_registry_resolves_each_known_format() -> None:
    assert registered_formats() == SOURCE_FORMATS
    for name, adapter_cls in ADAPTER_TYPES.items():
        adapter = get_adapter(name)
        assert isinstance(adapter, adapter_cls)
        assert adapter.source_format == name


def test_unsupported_format_fails_explicitly() -> None:
    with pytest.raises(UnsupportedFormatError, match="xlsx"):
        get_adapter("xlsx")


@pytest.mark.parametrize("fmt", ["pdf", "txt", "md", "pptx"])
def test_unimplemented_formats_fail_on_parse_and_apply(fmt: str, tmp_path: Path) -> None:
    adapter = get_adapter(fmt)
    with pytest.raises(NotImplementedError, match="not implemented"):
        adapter.parse(tmp_path / f"sample.{fmt}")
    with pytest.raises(NotImplementedError, match="not implemented"):
        adapter.apply(tmp_path / f"sample.{fmt}", [])


def test_docx_adapter_apply_writes_completed_file(tmp_path: Path) -> None:
    from tests.placement_helpers import ensure_placement_fixture, working_copy

    original = ensure_placement_fixture("blank_run.docx")
    ir = DocxAdapter().parse(original)
    space = next(s for s in ir.answer_spaces if s.type == "blank_run")
    copy_path = working_copy(original, tmp_path)
    adapter = get_adapter("docx")
    output = adapter.apply(
        copy_path,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="fill_existing",
                target=space.locator,
                text="Test",
            )
        ],
    )
    assert output.exists()
    assert output.name.endswith("_completed.docx")


def test_docx_adapter_parse_returns_document_ir() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "docx" / "simple_paragraphs.docx"
    if not fixture.exists():
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, str(fixture.parent / "generate_fixtures.py")],
            check=True,
        )
    adapter = get_adapter("docx")
    ir = adapter.parse(fixture)
    assert ir.source_format == "docx"
    assert ir.blocks


def test_docx_locator_helper_stays_inside_the_adapter() -> None:
    locator = make_docx_locator(
        DocxLocatorData(kind="paragraph", part="word/document.xml", body_index=3)
    )
    assert locator.adapter == DOCX_ADAPTER_NAME
    assert locator.payload["body_index"] == 3


def test_registry_contains_no_business_logic() -> None:
    source = REGISTRY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert function_names == {"registered_formats", "get_adapter"}

    called_attrs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called_attrs.add(node.func.attr)
    assert "parse" not in called_attrs
    assert "apply" not in called_attrs
    assert "preview_text" not in called_attrs
    assert "complete" not in called_attrs
    assert "plan_placements" not in called_attrs

    lowered = source.lower()
    for token in ("lxml", "python-docx", "zipfile", "openai", "ooxml"):
        assert token not in lowered
