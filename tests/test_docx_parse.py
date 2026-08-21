"""DOCX parser tests for Phase 2."""

from __future__ import annotations

import ast
import hashlib
import importlib
from pathlib import Path

import pytest

from docna.adapters.docx import DocxAdapter
from docna.adapters.docx.locators import (
    DOCX_ADAPTER_NAME,
    make_docx_locator,
    make_paragraph_locator,
    parse_docx_locator,
    resolve_locator,
    DocxLocatorData,
)
from docna.adapters.docx.parse import parse as parse_docx
from docna.ir import Block, DocumentIR, Locator

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "docx"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src" / "docna"

FIXTURE_NAMES = (
    "simple_paragraphs.docx",
    "headings.docx",
    "numbered_questions.docx",
    "blank_answers.docx",
    "tables.docx",
    "content_controls.docx",
    "nested_lists.docx",
    "mixed_document.docx",
)


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures() -> None:
    missing = [name for name in FIXTURE_NAMES if not (FIXTURE_DIR / name).exists()]
    if missing:
        generator = FIXTURE_DIR / "generate_fixtures.py"
        import subprocess
        import sys

        subprocess.run([sys.executable, str(generator)], check=True)


def _fixture(name: str) -> Path:
    path = FIXTURE_DIR / name
    assert path.exists(), f"Missing fixture: {path}"
    return path


def _parse(name: str) -> DocumentIR:
    return parse_docx(_fixture(name))


def test_source_file_is_not_modified_by_parsing() -> None:
    path = _fixture("simple_paragraphs.docx")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    parse_docx(path)
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == after


def test_paragraph_extraction() -> None:
    ir = _parse("simple_paragraphs.docx")
    paragraphs = [b for b in ir.blocks if b.kind == "paragraph"]
    assert len(paragraphs) == 3
    assert paragraphs[0].text.startswith("This is the first paragraph")
    assert all(block.locator.adapter == DOCX_ADAPTER_NAME for block in ir.blocks)


def test_heading_extraction_and_outline() -> None:
    ir = _parse("headings.docx")
    headings = [b for b in ir.blocks if b.kind == "heading"]
    assert len(headings) == 3
    assert ir.outline == [
        (headings[0].block_id, "Applicant Information"),
        (headings[1].block_id, "Contact Details"),
        (headings[2].block_id, "Employment History"),
    ]
    assert headings[0].style_name == "Heading 1"
    assert headings[1].style_name == "Heading 2"


def test_list_detection() -> None:
    ir = _parse("numbered_questions.docx")
    items = [b for b in ir.blocks if b.kind == "list_item"]
    assert len(items) == 3
    assert all(item.list_level == 0 for item in items)
    assert "full legal name" in items[0].text.lower()


def test_nested_list_levels() -> None:
    ir = _parse("nested_lists.docx")
    items = [b for b in ir.blocks if b.kind == "list_item"]
    assert len(items) >= 5
    levels = {item.list_level for item in items}
    assert 0 in levels
    assert 1 in levels
    nested = [item for item in items if item.list_level == 1]
    assert nested
    assert any(item.parent_block_id for item in nested)


def test_table_extraction() -> None:
    ir = _parse("tables.docx")
    assert len(ir.tables) == 1
    table = ir.tables[0]
    assert table.table_id == "tbl_0001"
    assert len(table.rows) == 3
    assert len(table.rows[0]) == 2
    assert table.header_row is True
    cells = [b for b in ir.blocks if b.kind == "table_cell"]
    assert len(cells) == 6


def test_empty_table_cells_become_answer_spaces() -> None:
    ir = _parse("tables.docx")
    table_spaces = [s for s in ir.answer_spaces if s.type == "table_cell"]
    assert table_spaces
    assert all(space.is_placeholder for space in table_spaces)
    assert all(space.locator.adapter == DOCX_ADAPTER_NAME for space in table_spaces)


def test_blank_runs_detected() -> None:
    ir = _parse("blank_answers.docx")
    blank_spaces = [s for s in ir.answer_spaces if s.type == "blank_run"]
    assert blank_spaces
    assert any("_" in space.current_text for space in blank_spaces)


def test_empty_paragraph_candidates() -> None:
    ir = _parse("blank_answers.docx")
    empty_spaces = [s for s in ir.answer_spaces if s.type == "empty_para"]
    assert empty_spaces


def test_answer_label_pattern_recorded() -> None:
    ir = _parse("blank_answers.docx")
    labels = [s for s in ir.answer_spaces if s.type == "none" and "answer" in s.current_text.lower()]
    assert labels


def test_content_controls_parsed() -> None:
    ir = _parse("content_controls.docx")
    control_spaces = [s for s in ir.answer_spaces if s.type == "content_control"]
    assert control_spaces
    assert any("click or tap" in space.current_text.lower() for space in control_spaces)


def test_deterministic_block_ids() -> None:
    first = _parse("mixed_document.docx")
    second = _parse("mixed_document.docx")
    assert [block.block_id for block in first.blocks] == [
        block.block_id for block in second.blocks
    ]


def test_deterministic_source_hash() -> None:
    path = _fixture("mixed_document.docx")
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    first = _parse("mixed_document.docx")
    second = _parse("mixed_document.docx")
    assert first.source_hash == expected
    assert second.source_hash == expected


def test_reading_order_is_stable() -> None:
    ir = _parse("mixed_document.docx")
    kinds = [block.kind for block in ir.blocks]
    assert kinds[0] == "heading"
    assert "table_cell" in kinds
    assert kinds.index("heading") < kinds.index("table_cell")


def test_every_block_has_opaque_locator() -> None:
    ir = _parse("mixed_document.docx")
    for block in ir.blocks:
        assert isinstance(block.locator, Locator)
        assert block.locator.adapter == DOCX_ADAPTER_NAME
        assert isinstance(block.locator.payload, dict)
        assert "body_index" in block.locator.payload


def test_every_answer_space_has_opaque_locator() -> None:
    ir = _parse("mixed_document.docx")
    for space in ir.answer_spaces:
        assert space.locator.adapter == DOCX_ADAPTER_NAME
        assert isinstance(space.locator.payload, dict)


def test_parsing_twice_produces_equivalent_ir() -> None:
    first = _parse("tables.docx")
    second = _parse("tables.docx")
    assert first.model_dump() == second.model_dump()


def test_preview_text_contains_block_and_space_ids() -> None:
    ir = _parse("blank_answers.docx")
    preview = DocxAdapter().preview_text(ir)
    assert "blk_0001" in preview
    assert "space_" in preview
    assert "document.xml" not in preview
    assert "w:p" not in preview


def test_preview_does_not_reread_source_file(monkeypatch: pytest.MonkeyPatch) -> None:
    ir = _parse("simple_paragraphs.docx")

    def fail_read(*_args, **_kwargs):
        raise AssertionError("preview_text must not read the DOCX file")

    monkeypatch.setattr(Path, "read_bytes", fail_read)
    preview = DocxAdapter().preview_text(ir)
    assert "blk_0001" in preview


def test_docx_locator_resolution_round_trip() -> None:
    path = _fixture("simple_paragraphs.docx")
    import zipfile

    with zipfile.ZipFile(path) as archive:
        part_xml = archive.read("word/document.xml")
    locator = make_paragraph_locator(0)
    element = resolve_locator(part_xml, locator)
    assert element.tag.endswith("}p")


def test_core_modules_do_not_import_python_docx() -> None:
    core_paths = [
        SRC / "ir.py",
        SRC / "pipeline.py",
        * (SRC / "detect").rglob("*.py"),
        * (SRC / "answer").rglob("*.py"),
        * (SRC / "place").rglob("*.py"),
    ]
    violations: list[str] = []
    for path in core_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] == "docx":
                        violations.append(f"{path.name} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".", 1)[0] == "docx":
                    violations.append(f"{path.name} imports from {node.module}")
    assert violations == []


def test_core_modules_do_not_inspect_locator_payload() -> None:
    forbidden = (
        'payload["body_index"]',
        "payload.get(",
        'payload["kind"]',
        "payload['body_index']",
    )
    core_paths = [
        SRC / "ir.py",
        SRC / "pipeline.py",
        * (SRC / "detect").rglob("*.py"),
        * (SRC / "answer").rglob("*.py"),
        * (SRC / "place").rglob("*.py"),
    ]
    hits: list[str] = []
    for path in core_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in source:
                hits.append(f"{path.name}: {token}")
    assert hits == []


def test_only_docx_adapter_package_imports_docx_library() -> None:
    allowed_prefix = SRC / "adapters" / "docx"
    violations: list[str] = []
    for path in SRC.rglob("*.py"):
        if allowed_prefix in path.parents or path.parent == allowed_prefix:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".", 1)[0] == "docx":
                        violations.append(f"{path} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".", 1)[0] == "docx":
                    violations.append(f"{path} imports from {node.module}")
    assert violations == []


def test_example_document_ir_from_mixed_fixture() -> None:
    ir = _parse("mixed_document.docx")
    assert ir.source_format == "docx"
    assert ir.blocks
    assert ir.tables
    assert ir.outline
    assert isinstance(ir, DocumentIR)


def test_make_docx_locator_uses_adapter_private_payload() -> None:
    locator = make_docx_locator(
        DocxLocatorData(kind="paragraph", part="word/document.xml", body_index=2)
    )
    data = parse_docx_locator(locator)
    assert data.body_index == 2
    assert locator.adapter == DOCX_ADAPTER_NAME
