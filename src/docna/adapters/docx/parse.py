"""Read-only DOCX parser producing DocumentIR with opaque locators."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree

from docna.adapters.docx.locators import (
    DOCX_MAIN_PART,
    NSMAP,
    W_NS,
    make_cell_locator,
    make_content_control_locator,
    make_paragraph_locator,
    make_run_range_locator,
)
from docna.ir import AnswerSpace, Block, DocumentIR, Locator, TableView

BLANK_RUN_RE = re.compile(r"^[\s_\-–—.]+$")
ANSWER_LABEL_RE = re.compile(r"^\s*answer\s*:\s*$", re.IGNORECASE)
ANSWER_LABEL_PREFIX_RE = re.compile(r"^\s*answer\s*:", re.IGNORECASE)
HEADING_STYLE_PREFIX = "Heading"
PLACEHOLDER_MARKERS = ("click or tap", "enter text", "your answer", "type here")


@dataclass
class _ParseState:
    blocks: list[Block] = field(default_factory=list)
    tables: list[TableView] = field(default_factory=list)
    answer_spaces: list[AnswerSpace] = field(default_factory=list)
    outline: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    block_seq: int = 0
    space_seq: int = 0
    table_seq: int = 0
    current_section_block_id: str | None = None
    list_parent_stack: list[str | None] = field(default_factory=list)


def parse(path: Path) -> DocumentIR:
    """Parse a DOCX file into DocumentIR without modifying the source file."""
    source_bytes = path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    document = Document(path)
    state = _ParseState()

    body = document.element.body
    for body_index, child in enumerate(body):
        tag = child.tag
        if tag == qn("w:p"):
            _parse_paragraph(Paragraph(child, document), body_index, state)
        elif tag == qn("w:tbl"):
            _parse_table(Table(child, document), body_index, state)
        elif tag == qn("w:sdt"):
            _parse_content_control(child, body_index, state)
        elif tag == qn("w:sectPr"):
            continue
        else:
            state.warnings.append(f"unsupported_body_element:{tag}")

    if document.sections and any(
        section.header or section.footer for section in document.sections
    ):
        state.warnings.append("headers_footers_skipped")

    return DocumentIR(
        document_id=f"doc_{source_hash[:16]}",
        source_format="docx",
        source_hash=source_hash,
        blocks=state.blocks,
        tables=state.tables,
        outline=state.outline,
        answer_spaces=state.answer_spaces,
        warnings=state.warnings,
    )


def _next_block_id(state: _ParseState) -> str:
    state.block_seq += 1
    return f"blk_{state.block_seq:04d}"


def _next_space_id(state: _ParseState) -> str:
    state.space_seq += 1
    return f"space_{state.space_seq:04d}"


def _next_table_id(state: _ParseState) -> str:
    state.table_seq += 1
    return f"tbl_{state.table_seq:04d}"


def _paragraph_text(paragraph: Paragraph) -> str:
    return paragraph.text or ""


def _paragraph_style_name(paragraph: Paragraph) -> str | None:
    try:
        if paragraph.style is None:
            return None
        return paragraph.style.name
    except (AttributeError, KeyError):
        return None


def _is_heading(paragraph: Paragraph) -> bool:
    style_name = _paragraph_style_name(paragraph)
    if style_name and style_name.startswith(HEADING_STYLE_PREFIX):
        return True
    p_pr = paragraph._p.pPr
    if p_pr is not None and p_pr.outlineLvl is not None:
        return True
    return False


def _list_level(paragraph: Paragraph) -> int | None:
    p_pr = paragraph._p.pPr
    if p_pr is not None and p_pr.numPr is not None:
        ilvl = p_pr.numPr.ilvl
        if ilvl is None:
            return 0
        return int(ilvl.val)

    style_name = _paragraph_style_name(paragraph)
    if not style_name:
        return None
    if style_name == "List Number" or style_name == "List Bullet":
        return 0
    for prefix in ("List Number ", "List Bullet "):
        if style_name.startswith(prefix):
            try:
                return int(style_name[len(prefix) :]) - 1
            except ValueError:
                return 0
    return None


def _update_list_parent(level: int | None, block_id: str, state: _ParseState) -> str | None:
    if level is None:
        state.list_parent_stack.clear()
        return None

    while len(state.list_parent_stack) > level + 1:
        state.list_parent_stack.pop()

    parent_id: str | None = None
    if level > 0:
        while len(state.list_parent_stack) < level:
            state.list_parent_stack.append(None)
        if len(state.list_parent_stack) >= level:
            parent_id = state.list_parent_stack[level - 1]

    while len(state.list_parent_stack) <= level:
        state.list_parent_stack.append(None)
    state.list_parent_stack[level] = block_id
    return parent_id


def _paragraph_kind(paragraph: Paragraph) -> str:
    if _is_heading(paragraph):
        return "heading"
    if _list_level(paragraph) is not None:
        return "list_item"
    return "paragraph"


def _role_hint_for_text(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None
    if stripped.endswith("?") or BLANK_RUN_RE.search(stripped):
        return "possible_question"
    if ANSWER_LABEL_RE.match(stripped):
        return "possible_blank"
    return None


def _iter_paragraph_runs(paragraph: Paragraph) -> Iterator[tuple[int, str]]:
    runs = paragraph.runs
    for index, run in enumerate(runs):
        yield index, run.text or ""


def _detect_blank_runs(
    paragraph: Paragraph,
    body_index: int,
    state: _ParseState,
    *,
    after_block_id: str | None = None,
) -> None:
    for run_index, run_text in _iter_paragraph_runs(paragraph):
        if not run_text:
            continue
        if not BLANK_RUN_RE.fullmatch(run_text):
            continue
        locator = make_run_range_locator(body_index, run_index, run_index)
        state.answer_spaces.append(
            AnswerSpace(
                space_id=_next_space_id(state),
                type="blank_run",
                locator=locator,
                current_text=run_text,
                is_placeholder=True,
                capacity_hint=len(run_text),
            )
        )


def _detect_empty_paragraph(
    paragraph: Paragraph,
    body_index: int,
    state: _ParseState,
) -> None:
    if _paragraph_text(paragraph).strip():
        return
    locator = make_paragraph_locator(body_index)
    state.answer_spaces.append(
        AnswerSpace(
            space_id=_next_space_id(state),
            type="empty_para",
            locator=locator,
            current_text="",
            is_placeholder=True,
        )
    )


def _parse_paragraph(paragraph: Paragraph, body_index: int, state: _ParseState) -> None:
    text = _paragraph_text(paragraph)
    list_level = _list_level(paragraph)
    kind = _paragraph_kind(paragraph)
    block_id = _next_block_id(state)
    parent_block_id = _update_list_parent(list_level, block_id, state)

    block = Block(
        block_id=block_id,
        kind=kind,  # type: ignore[arg-type]
        text=text,
        style_name=_paragraph_style_name(paragraph),
        list_level=list_level,
        parent_block_id=parent_block_id,
        locator=make_paragraph_locator(body_index),
        role_hint=_role_hint_for_text(text),  # type: ignore[arg-type]
    )
    state.blocks.append(block)

    if kind == "heading" and text.strip():
        state.outline.append((block_id, text.strip()))
        state.current_section_block_id = block_id

    if ANSWER_LABEL_RE.match(text.strip()) or ANSWER_LABEL_PREFIX_RE.match(text.strip()):
        label_text = "Answer:"
        if ANSWER_LABEL_PREFIX_RE.match(text.strip()):
            match = ANSWER_LABEL_PREFIX_RE.match(text.strip())
            assert match is not None
            label_text = text.strip()[: match.end()].strip()
            if not label_text.endswith(":"):
                label_text = f"{label_text}:"
        locator = make_paragraph_locator(body_index)
        state.answer_spaces.append(
            AnswerSpace(
                space_id=_next_space_id(state),
                type="none",
                locator=locator,
                current_text=label_text,
                is_placeholder=False,
            )
        )

    _detect_blank_runs(paragraph, body_index, state, after_block_id=block_id)
    _detect_empty_paragraph(paragraph, body_index, state)


def _table_header_row(table: Table) -> bool:
    if len(table.rows) < 2:
        return False
    first_row_texts = [cell.text.strip() for cell in table.rows[0].cells]
    if not any(first_row_texts):
        return False
    second_row_texts = [cell.text.strip() for cell in table.rows[1].cells]
    if any(not text for text in second_row_texts) and all(first_row_texts):
        return True
    return _row_cells_look_like_header(table.rows[0])


def _row_cells_look_like_header(row) -> bool:
    bold_count = 0
    non_empty = 0
    for cell in row.cells:
        text = cell.text.strip()
        if not text:
            continue
        non_empty += 1
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                if run.bold:
                    bold_count += 1
                    break
    return non_empty > 0 and bold_count >= max(1, non_empty // 2)


def _parse_table(table: Table, body_index: int, state: _ParseState) -> None:
    table_id = _next_table_id(state)
    rows: list[list[str]] = []
    cell_locators: dict[tuple[int, int], Locator] = {}
    header_row = _table_header_row(table)

    for row_index, row in enumerate(table.rows):
        row_block_ids: list[str] = []
        for col_index, cell in enumerate(row.cells):
            cell_text = cell.text or ""
            block_id = _next_block_id(state)
            row_block_ids.append(block_id)
            locator = make_cell_locator(body_index, row_index, col_index)
            cell_locators[(row_index, col_index)] = locator

            block = Block(
                block_id=block_id,
                kind="table_cell",
                text=cell_text,
                style_name=_cell_style_name(cell),
                list_level=None,
                parent_block_id=state.current_section_block_id,
                locator=locator,
                role_hint=_role_hint_for_text(cell_text),  # type: ignore[arg-type]
            )
            state.blocks.append(block)

            if not cell_text.strip():
                state.answer_spaces.append(
                    AnswerSpace(
                        space_id=_next_space_id(state),
                        type="table_cell",
                        locator=locator,
                        current_text="",
                        is_placeholder=True,
                    )
                )
            else:
                _detect_blank_runs_in_cell(cell, body_index, row_index, col_index, state)

        rows.append(row_block_ids)

    state.tables.append(
        TableView(
            table_id=table_id,
            rows=rows,
            cell_locators=cell_locators,
            header_row=header_row,
        )
    )


def _cell_style_name(cell) -> str | None:
    if not cell.paragraphs:
        return None
    return _paragraph_style_name(cell.paragraphs[0])


def _detect_blank_runs_in_cell(
    cell,
    body_index: int,
    row_index: int,
    col_index: int,
    state: _ParseState,
) -> None:
    for paragraph in cell.paragraphs:
        for run_index, run_text in _iter_paragraph_runs(paragraph):
            if not run_text or not BLANK_RUN_RE.fullmatch(run_text):
                continue
            locator = make_cell_locator(body_index, row_index, col_index)
            state.answer_spaces.append(
                AnswerSpace(
                    space_id=_next_space_id(state),
                    type="blank_run",
                    locator=locator,
                    current_text=run_text,
                    is_placeholder=True,
                    capacity_hint=len(run_text),
                )
            )


def _parse_content_control(element: etree._Element, body_index: int, state: _ParseState) -> None:
    text = _sdt_text(element)
    block_id = _next_block_id(state)
    block = Block(
        block_id=block_id,
        kind="paragraph",
        text=text,
        style_name=None,
        list_level=None,
        parent_block_id=state.current_section_block_id,
        locator=make_content_control_locator(body_index),
        role_hint="possible_blank" if _looks_like_placeholder(text) else None,
    )
    state.blocks.append(block)

    if _looks_like_placeholder(text) or not text.strip():
        state.answer_spaces.append(
            AnswerSpace(
                space_id=_next_space_id(state),
                type="content_control",
                locator=make_content_control_locator(body_index),
                current_text=text,
                is_placeholder=True,
            )
        )


def _sdt_text(element: etree._Element) -> str:
    content = element.find("w:sdtContent", namespaces=NSMAP)
    if content is None:
        return ""
    texts = content.xpath(".//w:t/text()", namespaces=NSMAP)
    return "".join(texts)


def _looks_like_placeholder(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return True
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)
