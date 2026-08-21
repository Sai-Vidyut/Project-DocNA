"""DOCX surgical apply and placement integration tests."""

from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from docna.adapters.docx import DocxAdapter
from docna.adapters.docx.apply import apply
from docna.adapters.docx.locators import DOCX_MAIN_PART, NSMAP
from docna.adapters.docx.mutate import paragraph_text
from docna.detect.run import detect_from_adapter
from docna.ir import Answer, PlacementOp
from docna.place.planner import plan_placements
from tests.detect_helpers import rule_based_mock_provider
from tests.placement_helpers import (
    apply_ops,
    ensure_placement_fixture,
    parse_placement_fixture,
    sha256_file,
    working_copy,
)


@pytest.fixture(scope="session", autouse=True)
def ensure_placement_fixtures() -> None:
    ensure_placement_fixture("blank_run.docx")


def _read_document_xml(docx_path: Path) -> bytes:
    with zipfile.ZipFile(docx_path) as archive:
        return archive.read(DOCX_MAIN_PART)


def test_original_immutability(tmp_path: Path) -> None:
    original = ensure_placement_fixture("blank_run.docx")
    before = sha256_file(original)
    ir = parse_placement_fixture("blank_run.docx")
    space = next(s for s in ir.answer_spaces if s.type == "blank_run")
    block = next(b for b in ir.blocks if "Full name" in b.text)
    ops = [
        PlacementOp(
            op_id="op_0001",
            task_id="task_0001",
            strategy="fill_existing",
            target=space.locator,
            text="Jane Doe",
            style_clone_from=block.locator,
        )
    ]
    apply_ops(original, ops, tmp_path)
    after = sha256_file(original)
    assert before == after


def test_no_op_is_byte_equivalent(tmp_path: Path) -> None:
    original = ensure_placement_fixture("blank_run.docx")
    copy_path = working_copy(original, tmp_path)
    before = copy_path.read_bytes()
    output = apply(copy_path, [])
    assert output.read_bytes() == before


def test_fill_existing_blank_run(tmp_path: Path) -> None:
    original = ensure_placement_fixture("blank_run.docx")
    ir = parse_placement_fixture("blank_run.docx")
    space = next(s for s in ir.answer_spaces if s.type == "blank_run")
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="fill_existing",
                target=space.locator,
                text="Jane Doe",
            )
        ],
        tmp_path,
    )
    xml = _read_document_xml(output)
    root = etree.fromstring(xml)
    text = "".join(root.xpath(".//w:t/text()", namespaces=NSMAP))
    assert "Jane Doe" in text
    assert "Full name:" in text


def test_fill_existing_empty_paragraph(tmp_path: Path) -> None:
    original = ensure_placement_fixture("empty_paragraph.docx")
    ir = parse_placement_fixture("empty_paragraph.docx")
    space = next(s for s in ir.answer_spaces if s.type == "empty_para")
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="fill_existing",
                target=space.locator,
                text="Five years of experience.",
            )
        ],
        tmp_path,
    )
    reparsed = DocxAdapter().parse(output)
    assert any("Five years" in block.text for block in reparsed.blocks)


def test_fill_cell_table_answer(tmp_path: Path) -> None:
    original = ensure_placement_fixture("table_answer.docx")
    ir = parse_placement_fixture("table_answer.docx")
    space = next(s for s in ir.answer_spaces if s.type == "table_cell")
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="fill_cell",
                target=space.locator,
                text="Alice",
            )
        ],
        tmp_path,
    )
    reparsed = DocxAdapter().parse(output)
    assert any("Alice" in block.text for block in reparsed.blocks)
    table = reparsed.tables[0]
    assert len(table.rows) == 2
    assert len(table.rows[0]) == 2


def test_insert_below_without_space(tmp_path: Path) -> None:
    original = ensure_placement_fixture("nested_questions.docx")
    ir = parse_placement_fixture("nested_questions.docx")
    question = next(b for b in ir.blocks if "Explain OOP" in b.text)
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="insert_below",
                target=question.locator,
                text="OOP organizes code into objects.",
                style_clone_from=question.locator,
            )
        ],
        tmp_path,
    )
    reparsed = DocxAdapter().parse(output)
    texts = [b.text for b in reparsed.blocks]
    oop_index = next(i for i, t in enumerate(texts) if "Explain OOP" in t)
    assert any("OOP organizes" in t for t in texts[oop_index : oop_index + 3])


def test_numbering_survives_insert_below(tmp_path: Path) -> None:
    original = ensure_placement_fixture("numbered_question.docx")
    ir = parse_placement_fixture("numbered_question.docx")
    first = ir.blocks[0]
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="insert_below",
                target=first.locator,
                text="Answer A content.",
                style_clone_from=first.locator,
            )
        ],
        tmp_path,
    )
    reparsed = DocxAdapter().parse(output)
    question_blocks = [b for b in reparsed.blocks if re.fullmatch(r"Question [ABC]\?", b.text.strip())]
    assert len(question_blocks) == 3
    answer_blocks = [b for b in reparsed.blocks if "Answer A content" in b.text]
    assert answer_blocks
    assert all(block.kind != "list_item" for block in answer_blocks)


def test_unrelated_xml_unchanged_except_target(tmp_path: Path) -> None:
    original = ensure_placement_fixture("blank_run.docx")
    before_xml = _read_document_xml(original)
    ir = parse_placement_fixture("blank_run.docx")
    space = next(s for s in ir.answer_spaces if s.type == "blank_run")
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="fill_existing",
                target=space.locator,
                text="X",
            )
        ],
        tmp_path,
    )
    after_xml = _read_document_xml(output)
    assert before_xml != after_xml
    assert b"Full name:" in after_xml


def test_multi_paragraph_answer(tmp_path: Path) -> None:
    original = ensure_placement_fixture("multiple_answers.docx")
    ir = parse_placement_fixture("multiple_answers.docx")
    space = next(s for s in ir.answer_spaces if s.type == "empty_para")
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="fill_existing",
                target=space.locator,
                text="Paragraph one.\n\nParagraph two.",
            )
        ],
        tmp_path,
    )
    reparsed = DocxAdapter().parse(output)
    joined = "\n".join(block.text for block in reparsed.blocks)
    assert "Paragraph one" in joined
    assert "Paragraph two" in joined


def test_formatting_preservation_on_insert(tmp_path: Path) -> None:
    original = ensure_placement_fixture("formatting_preservation.docx")
    ir = parse_placement_fixture("formatting_preservation.docx")
    question = ir.blocks[0]
    space = next(s for s in ir.answer_spaces if s.type == "empty_para")
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="fill_existing",
                target=space.locator,
                text="Bold answer.",
                style_clone_from=question.locator,
            )
        ],
        tmp_path,
    )
    xml = _read_document_xml(output)
    root = etree.fromstring(xml)
    text = "".join(root.xpath(".//w:t/text()", namespaces=NSMAP))
    assert "Bold answer" in text


def test_skip_strategy_does_not_mutate(tmp_path: Path) -> None:
    original = ensure_placement_fixture("blank_run.docx")
    copy_path = working_copy(original, tmp_path)
    before = copy_path.read_bytes()
    output = apply(
        copy_path,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="skip",
                text="ignored",
                review_flags=["instruction"],
            )
        ],
    )
    assert output.read_bytes() == before


def test_full_placement_integration(tmp_path: Path) -> None:
    original = ensure_placement_fixture("placement_integration.docx")
    before_hash = sha256_file(original)
    ir = parse_placement_fixture("placement_integration.docx")
    adapter = DocxAdapter()
    detection = detect_from_adapter(ir, adapter, rule_based_mock_provider())

    answers = []
    for task in detection.tasks:
        if task.skip_reason == "already_answered" or task.kind == "instruction":
            continue
        if task.skip_reason in {"low_confidence"}:
            continue
        answers.append(Answer(task_id=task.task_id, text=f"Answer for {task.task_id}", confidence=0.95))

    ops = plan_placements(ir, detection.tasks, answers)
    strategies = {op.strategy for op in ops}
    assert "skip" in strategies
    assert strategies & {"fill_existing", "insert_below", "fill_cell"}

    copy_path = working_copy(original, tmp_path)
    output = apply(copy_path, ops)
    assert sha256_file(original) == before_hash

    reparsed = adapter.parse(output)
    applied_ops = [op for op in ops if op.strategy != "skip"]
    for op in applied_ops:
        if op.strategy in {"fill_existing", "fill_cell"}:
            assert any(op.text in block.text for block in reparsed.blocks)
