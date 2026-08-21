"""Render DocumentIR preview text for semantic detection."""

from __future__ import annotations

from collections import defaultdict

from docna.adapters.docx.locators import DOCX_ADAPTER_NAME, parse_docx_locator
from docna.ir import DocumentIR


def render_preview(ir: DocumentIR) -> str:
    """Build a numbered preview from DocumentIR without reading the source file."""
    if not all(block.locator.adapter == DOCX_ADAPTER_NAME for block in ir.blocks):
        return _render_generic_preview(ir)
    if ir.answer_spaces and not all(
        space.locator.adapter == DOCX_ADAPTER_NAME for space in ir.answer_spaces
    ):
        return _render_generic_preview(ir)

    lines: list[str] = []
    spaces_by_locator: dict[tuple[str, tuple[tuple[str, object], ...]], list[str]] = defaultdict(list)

    for space in ir.answer_spaces:
        anchor = _space_anchor_label(space.type, space.current_text)
        label = f"[{space.space_id}: {space.type}"
        if anchor:
            label += f" {anchor}"
        label += "]"
        spaces_by_locator[_locator_key(space.locator)].append(f"    {label}")

    table_positions: dict[str, tuple[str, int, int]] = {}
    for table in ir.tables:
        for row_index, row in enumerate(table.rows):
            for col_index, block_id in enumerate(row):
                table_positions[block_id] = (table.table_id, row_index, col_index)

    for block in ir.blocks:
        block_key = _locator_key(block.locator)
        attached_spaces = list(spaces_by_locator.get(block_key, []))
        data = parse_docx_locator(block.locator)
        if block.kind != "table_cell":
            for key, labels in list(spaces_by_locator.items()):
                if not labels:
                    continue
                payload = dict(key[1])
                if payload.get("body_index") == data.body_index and payload.get("kind") == "run_range":
                    attached_spaces.extend(labels)
                    spaces_by_locator[key] = []

        if block.block_id in table_positions:
            table_id, row_index, col_index = table_positions[block.block_id]
            cell_text = block.text.strip()
            line = f"[{table_id} r{row_index}c{col_index}] {cell_text}".rstrip()
            if attached_spaces:
                line += "\n" + "\n".join(attached_spaces)
                spaces_by_locator.pop(block_key, None)
            lines.append(line)
            continue

        kind_label = _block_kind_label(block)
        indent = "    " * (block.list_level or 0) if block.kind == "list_item" else ""
        line = f"{indent}[{block.block_id} {kind_label}] {block.text}".rstrip()
        if attached_spaces:
            line += "\n" + "\n".join(attached_spaces)
            spaces_by_locator.pop(block_key, None)
        lines.append(line)

    for leftover in spaces_by_locator.values():
        lines.extend(leftover)

    if ir.outline:
        lines.append("")
        lines.append("[outline]")
        for heading_id, title in ir.outline:
            lines.append(f"  {heading_id}: {title}")

    return "\n".join(lines).strip() + "\n"


def _render_generic_preview(ir: DocumentIR) -> str:
    lines: list[str] = []
    for block in ir.blocks:
        lines.append(f"[{block.block_id} {block.kind}] {block.text}")
    for table in ir.tables:
        for row_index, row in enumerate(table.rows):
            for col_index, cell in enumerate(row):
                lines.append(f"[{table.table_id} r{row_index}c{col_index}] {cell}")
    for space in ir.answer_spaces:
        lines.append(f"[{space.space_id} {space.type}] {space.current_text}")
    return "\n".join(lines)


def _block_kind_label(block) -> str:
    if block.kind == "list_item":
        return "list"
    if block.kind == "heading":
        return "heading"
    return "para"


def _space_anchor_label(space_type: str, current_text: str) -> str:
    if space_type == "blank_run" and current_text:
        return f'"{current_text}"'
    if current_text.strip():
        return f'"{current_text.strip()}"'
    return ""


def _locator_key(locator) -> tuple[str, tuple[tuple[str, object], ...]]:
    return (locator.adapter, tuple(sorted(locator.payload.items())))
