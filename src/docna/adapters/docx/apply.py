"""Surgical OOXML write-back onto a working copy.

The original file must remain immutable. This module copies the DOCX package and
edits ``word/document.xml`` in place. It never regenerates a document from IR.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from docna.adapters.docx.locators import (
    DOCX_ADAPTER_NAME,
    DOCX_MAIN_PART,
    NSMAP,
    parse_docx_locator,
    resolve_locator_on_body,
)
from docna.adapters.docx.mutate import (
    insert_paragraphs_after,
    paragraph_text,
    replace_sdt_text,
    set_cell_text,
    set_paragraph_text,
    set_run_text,
    strip_numbering,
)
from docna.ir import PlacementOp
from docna.place.answer_text import split_answer_paragraphs


class PlacementApplyError(Exception):
    """Raised when a placement operation cannot be applied safely."""


@dataclass(slots=True)
class _ResolvedOp:
    op: PlacementOp
    target: etree._Element
    style_source: etree._Element | None


def apply(source_copy: Path, ops: Sequence[PlacementOp]) -> Path:
    """Apply placement ops to a working copy and return the output path."""
    if not source_copy.exists():
        raise PlacementApplyError(f"Working copy does not exist: {source_copy}")

    output_dir = source_copy.parent
    final_output = output_dir / f"{source_copy.stem}_completed.docx"

    with tempfile.NamedTemporaryFile(
        suffix=".docx",
        dir=output_dir,
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        shutil.copy2(source_copy, tmp_path)
        active_ops = [op for op in ops if op.strategy != "skip"]
        if not active_ops:
            tmp_path.replace(final_output)
            return final_output

        _apply_ops_to_package(tmp_path, active_ops)
        tmp_path.replace(final_output)
        return final_output
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def _apply_ops_to_package(package_path: Path, ops: Sequence[PlacementOp]) -> None:
    with zipfile.ZipFile(package_path, "r") as archive:
        if DOCX_MAIN_PART not in archive.namelist():
            raise PlacementApplyError("DOCX package is missing word/document.xml")
        original_xml = archive.read(DOCX_MAIN_PART)
        other_files = {
            name: archive.read(name)
            for name in archive.namelist()
            if name != DOCX_MAIN_PART
        }

    root = etree.fromstring(original_xml)
    body = root.find("w:body", namespaces=NSMAP)
    if body is None:
        raise PlacementApplyError("DOCX main document part is missing w:body")

    resolved_ops: list[_ResolvedOp] = []
    for op in ops:
        _validate_op(op)
        target = resolve_locator_on_body(body, op.target)  # type: ignore[arg-type]
        style_source = None
        if op.style_clone_from is not None:
            try:
                style_source = resolve_locator_on_body(body, op.style_clone_from)
            except ValueError:
                style_source = None
        resolved_ops.append(_ResolvedOp(op=op, target=target, style_source=style_source))

    chain_heads: dict[str, etree._Element] = {}
    for resolved in resolved_ops:
        _apply_single_op(body, resolved, chain_heads=chain_heads)

    modified_xml = etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(DOCX_MAIN_PART, modified_xml)
        for name, data in other_files.items():
            archive.writestr(name, data)


def _validate_op(op: PlacementOp) -> None:
    if op.target is None:
        raise PlacementApplyError(f"Operation {op.op_id} is missing a target locator")
    if op.target.adapter != DOCX_ADAPTER_NAME:
        raise PlacementApplyError(
            f"Operation {op.op_id} targets non-docx locator {op.target.adapter!r}"
        )


def _apply_single_op(
    body: etree._Element,
    resolved: _ResolvedOp,
    *,
    chain_heads: dict[str, etree._Element],
) -> None:
    op = resolved.op
    data = parse_docx_locator(op.target)  # type: ignore[arg-type]
    element = resolved.target
    paragraphs = split_answer_paragraphs(op.text)

    if op.strategy == "fill_existing":
        if data.kind == "run_range":
            set_run_text(element, op.text)
            return
        if data.kind == "content_control":
            replace_sdt_text(element, op.text)
            return
        if data.kind == "paragraph":
            first_text = paragraphs[0] if paragraphs else op.text
            first_text = _preserve_answer_label(element, first_text)
            set_paragraph_text(element, first_text)
            if len(paragraphs) > 1:
                insert_paragraphs_after(
                    body,
                    element,
                    paragraphs[1:],
                    style_source=resolved.style_source,
                    strip_numpr=True,
                )
            return
        raise PlacementApplyError(f"Unsupported fill_existing target kind: {data.kind}")

    if op.strategy == "fill_cell":
        set_cell_text(element, op.text)
        return

    if op.strategy == "insert_below":
        paragraph = _resolve_insert_paragraph(element)
        strip_numbering(paragraph)
        anchor = paragraph
        chain_key = _insert_chain_key(op.target)  # type: ignore[arg-type]
        if chain_key and "chain_insert" in op.review_flags and chain_key in chain_heads:
            anchor = chain_heads[chain_key]
        first_text = paragraphs[0] if paragraphs else op.text
        inserted = insert_paragraphs_after(
            body,
            anchor,
            [first_text, *paragraphs[1:]],
            style_source=resolved.style_source if resolved.style_source is not None else paragraph,
            strip_numpr=True,
        )
        if chain_key and inserted and "shared_answer_space" in op.review_flags:
            chain_heads[chain_key] = inserted[-1]
        return

    raise PlacementApplyError(f"Unsupported placement strategy: {op.strategy}")


def _preserve_answer_label(paragraph: etree._Element, answer_text: str) -> str:
    """Keep explicit Answer: labels when filling a label-only answer field."""
    existing = paragraph_text(paragraph).strip()
    if not existing.lower().startswith("answer"):
        return answer_text
    if answer_text.strip().lower().startswith("answer"):
        return answer_text
    label = existing.splitlines()[0].strip()
    if not label.endswith(":"):
        return answer_text
    remainder = existing[len(label) :].strip()
    if remainder:
        return answer_text
    return f"{label}\n{answer_text}"


def _insert_chain_key(locator) -> str | None:
    data = parse_docx_locator(locator)
    if data.kind == "paragraph":
        return f"p:{data.body_index}"
    return None


def _resolve_insert_paragraph(element: etree._Element):
    if element.tag.endswith("}p"):
        return element
    if element.tag.endswith("}tc"):
        paragraphs = element.findall(".//w:p", namespaces=NSMAP)
        if not paragraphs:
            raise PlacementApplyError("Table cell has no paragraph for insert_below")
        return paragraphs[-1]
    raise PlacementApplyError("insert_below target is not a paragraph or cell")

