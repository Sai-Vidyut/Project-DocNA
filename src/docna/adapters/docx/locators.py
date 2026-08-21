"""DOCX-specific locator payloads and resolution helpers.

This module is private to the DOCX adapter. Core code (detect, answer, place,
pipeline, ir) must not import it. Locator payloads are opaque to the core but
carry enough information for ``apply()`` to find the exact XML node later.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from lxml import etree
from lxml.etree import _Element  # type: ignore[attr-defined]

from docna.ir import Locator

DOCX_ADAPTER_NAME = "docx"
DOCX_MAIN_PART = "word/document.xml"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": W_NS}

DocxLocatorKind = Literal[
    "paragraph",
    "run_range",
    "cell",
    "content_control",
    "bookmark",
]

PAYLOAD_VERSION = 1


@dataclass(frozen=True, slots=True)
class DocxLocatorData:
    """Adapter-private locator fields. Never imported by core modules."""

    kind: DocxLocatorKind
    part: str
    body_index: int
    run_start: int | None = None
    run_end: int | None = None
    row: int | None = None
    col: int | None = None
    sdt_index: int | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "v": PAYLOAD_VERSION,
            "kind": self.kind,
            "part": self.part,
            "body_index": self.body_index,
        }
        if self.run_start is not None:
            payload["run_start"] = self.run_start
        if self.run_end is not None:
            payload["run_end"] = self.run_end
        if self.row is not None:
            payload["row"] = self.row
        if self.col is not None:
            payload["col"] = self.col
        if self.sdt_index is not None:
            payload["sdt_index"] = self.sdt_index
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> DocxLocatorData:
        return cls(
            kind=cast(DocxLocatorKind, payload["kind"]),
            part=str(payload["part"]),
            body_index=int(payload["body_index"]),
            run_start=_optional_int(payload.get("run_start")),
            run_end=_optional_int(payload.get("run_end")),
            row=_optional_int(payload.get("row")),
            col=_optional_int(payload.get("col")),
            sdt_index=_optional_int(payload.get("sdt_index")),
        )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def make_docx_locator(data: DocxLocatorData) -> Locator:
    """Wrap adapter-private locator data in an opaque Locator."""
    return Locator(adapter=DOCX_ADAPTER_NAME, payload=data.to_payload())


def make_paragraph_locator(body_index: int) -> Locator:
    return make_docx_locator(
        DocxLocatorData(kind="paragraph", part=DOCX_MAIN_PART, body_index=body_index)
    )


def make_run_range_locator(body_index: int, run_start: int, run_end: int) -> Locator:
    return make_docx_locator(
        DocxLocatorData(
            kind="run_range",
            part=DOCX_MAIN_PART,
            body_index=body_index,
            run_start=run_start,
            run_end=run_end,
        )
    )


def make_cell_locator(body_index: int, row: int, col: int) -> Locator:
    return make_docx_locator(
        DocxLocatorData(
            kind="cell",
            part=DOCX_MAIN_PART,
            body_index=body_index,
            row=row,
            col=col,
        )
    )


def make_content_control_locator(body_index: int, sdt_index: int = 0) -> Locator:
    return make_docx_locator(
        DocxLocatorData(
            kind="content_control",
            part=DOCX_MAIN_PART,
            body_index=body_index,
            sdt_index=sdt_index,
        )
    )


def parse_docx_locator(locator: Locator) -> DocxLocatorData:
    """Decode a Locator minted by this adapter. Adapter-internal use only."""
    if locator.adapter != DOCX_ADAPTER_NAME:
        raise ValueError(f"Expected adapter {DOCX_ADAPTER_NAME!r}, got {locator.adapter!r}")
    return DocxLocatorData.from_payload(locator.payload)


def load_document_body(part_xml: bytes) -> _Element:
    root = etree.fromstring(part_xml)
    body = root.find("w:body", namespaces=NSMAP)
    if body is None:
        raise ValueError("DOCX main document part is missing w:body")
    return body


def resolve_locator_on_body(body: _Element, locator: Locator) -> _Element:
    """Resolve a locator against a live document body element."""
    data = parse_docx_locator(locator)
    children = list(body)
    if data.body_index < 0 or data.body_index >= len(children):
        raise ValueError(f"body_index {data.body_index} is out of range")

    element = children[data.body_index]

    if data.kind == "paragraph":
        return _resolve_paragraph(element)

    if data.kind == "run_range":
        paragraph = _resolve_paragraph(element)
        runs = paragraph.findall("w:r", namespaces=NSMAP)
        if data.run_start is None or data.run_end is None:
            raise ValueError("run_range locator requires run_start and run_end")
        if data.run_start >= len(runs) or data.run_end >= len(runs):
            raise ValueError("run index is out of range")
        return runs[data.run_start]

    if data.kind == "cell":
        table = _resolve_table(element)
        if data.row is None or data.col is None:
            raise ValueError("cell locator requires row and col")
        rows = table.findall("w:tr", namespaces=NSMAP)
        if data.row >= len(rows):
            raise ValueError("row index is out of range")
        cells = rows[data.row].findall("w:tc", namespaces=NSMAP)
        if data.col >= len(cells):
            raise ValueError("column index is out of range")
        return cells[data.col]

    if data.kind == "content_control":
        sdt = _resolve_sdt(element)
        if data.sdt_index:
            sdts = sdt.findall(".//w:sdt", namespaces=NSMAP)
            if data.sdt_index >= len(sdts):
                raise ValueError("sdt_index is out of range")
            return sdts[data.sdt_index]
        return sdt

    raise ValueError(f"Unsupported locator kind: {data.kind}")


def resolve_locator(part_xml: bytes, locator: Locator) -> _Element:
    """Resolve a DOCX locator to its XML element. Used by apply() in Phase 4."""
    data = parse_docx_locator(locator)
    if data.part != DOCX_MAIN_PART:
        raise ValueError(f"Unsupported document part: {data.part}")

    body = load_document_body(part_xml)
    return resolve_locator_on_body(body, locator)


def _resolve_paragraph(element: _Element) -> _Element:
    if element.tag != f"{{{W_NS}}}p":
        raise ValueError("Locator does not refer to a paragraph")
    return element


def _resolve_table(element: _Element) -> _Element:
    if element.tag != f"{{{W_NS}}}tbl":
        raise ValueError("Locator does not refer to a table")
    return element


def _resolve_sdt(element: _Element) -> _Element:
    if element.tag != f"{{{W_NS}}}sdt":
        raise ValueError("Locator does not refer to a content control")
    return element
