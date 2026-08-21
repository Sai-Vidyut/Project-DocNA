"""Low-level OOXML mutation helpers for surgical DOCX write-back."""

from __future__ import annotations

import copy
from typing import Iterable

from lxml import etree
from lxml.etree import _Element  # type: ignore[attr-defined]

from docna.adapters.docx.locators import NSMAP, W_NS

W_P = f"{{{W_NS}}}p"
W_R = f"{{{W_NS}}}r"
W_T = f"{{{W_NS}}}t"
W_PPR = f"{{{W_NS}}}pPr"
W_NUMPR = f"{{{W_NS}}}numPr"
W_PSTYLE = f"{{{W_NS}}}pStyle"
W_VAL = f"{{{W_NS}}}val"


def paragraph_text(paragraph: _Element) -> str:
    return "".join(paragraph.xpath(".//w:t/text()", namespaces=NSMAP))


def set_run_text(run: _Element, text: str) -> None:
    text_nodes = run.findall(W_T, namespaces=NSMAP)
    if not text_nodes:
        text_node = etree.SubElement(run, W_T)
        text_nodes = [text_node]
    text_nodes[0].text = text
    text_nodes[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for extra in text_nodes[1:]:
        run.remove(extra)


def set_paragraph_text(paragraph: _Element, text: str) -> None:
    for child in list(paragraph):
        if child.tag == W_R:
            paragraph.remove(child)
    if not text:
        return
    run = etree.SubElement(paragraph, W_R)
    set_run_text(run, text)


def set_cell_text(cell: _Element, text: str) -> None:
    paragraphs = cell.findall(W_P, namespaces=NSMAP)
    if not paragraphs:
        paragraph = etree.SubElement(cell, W_P)
        set_paragraph_text(paragraph, text)
        return
    set_paragraph_text(paragraphs[0], text)
    for extra in paragraphs[1:]:
        cell.remove(extra)


def strip_numbering(paragraph: _Element) -> None:
    p_pr = paragraph.find(W_PPR, namespaces=NSMAP)
    if p_pr is None:
        return
    num_pr = p_pr.find(W_NUMPR, namespaces=NSMAP)
    if num_pr is not None:
        p_pr.remove(num_pr)
    p_style = p_pr.find(W_PSTYLE, namespaces=NSMAP)
    if p_style is not None:
        style_val = p_style.get(W_VAL, "")
        if "list" in style_val.lower():
            p_pr.remove(p_style)


def clone_paragraph(paragraph: _Element, *, strip_numpr: bool = False) -> _Element:
    cloned = copy.deepcopy(paragraph)
    if strip_numpr:
        strip_numbering(cloned)
    return cloned


def insert_paragraphs_after(
    body: _Element,
    after_paragraph: _Element,
    paragraphs_text: Iterable[str],
    *,
    style_source: _Element | None = None,
    strip_numpr: bool = True,
) -> list[_Element]:
    source = style_source if style_source is not None else after_paragraph
    inserted: list[_Element] = []
    insert_index = list(body).index(after_paragraph) + 1

    for chunk in paragraphs_text:
        if not chunk:
            continue
        new_para = clone_paragraph(source, strip_numpr=strip_numpr)
        set_paragraph_text(new_para, chunk)
        body.insert(insert_index, new_para)
        inserted.append(new_para)
        insert_index += 1

    return inserted


def replace_sdt_text(sdt: _Element, text: str) -> None:
    content = sdt.find("w:sdtContent", namespaces=NSMAP)
    if content is None:
        content = etree.SubElement(sdt, f"{{{W_NS}}}sdtContent")
    for child in list(content):
        content.remove(child)
    paragraph = etree.SubElement(content, W_P)
    set_paragraph_text(paragraph, text)
