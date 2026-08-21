"""Regression tests for answer presence validation after placement."""

from __future__ import annotations

from pathlib import Path

import pytest

from docna.adapters.docx import DocxAdapter
from docna.ir import Locator, PlacementOp
from docna.place.answer_text import answer_text_present
from tests.placement_helpers import apply_ops, ensure_placement_fixture
from tests.realworld_helpers import ensure_realworld_fixture


def test_answer_text_present_accepts_multi_paragraph_insert_below() -> None:
    text = (
        "Government policy influences inflation primarily through monetary and fiscal tools. "
        "Tightening policy reduces excess demand.\n\n"
        "In summary, government policy acts as a lever to influence demand."
    )
    op = PlacementOp(
        op_id="op_0001",
        task_id="task_0002",
        strategy="insert_below",
        target=Locator(adapter="docx", payload={"kind": "paragraph", "body_index": 1}),
        text=text,
    )
    block_text = (
        "What role does government policy play in inflation?\n"
        "Government policy influences inflation primarily through monetary and fiscal tools. "
        "Tightening policy reduces excess demand.\n"
        "In summary, government policy acts as a lever to influence demand."
    )
    assert answer_text_present(op, block_text)


def test_answer_text_present_accepts_multi_paragraph_fill_existing(tmp_path: Path) -> None:
    original = ensure_placement_fixture("empty_paragraph.docx")
    ir = DocxAdapter().parse(original)
    space = next(s for s in ir.answer_spaces if s.type == "empty_para")
    answer = (
        "Here is the pseudocode for breadth-first search (BFS):\n\n"
        "```\nBFS(graph, start_node)\n    Initialize a queue\n```\n\n"
        "This implementation uses a FIFO queue."
    )
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0004",
                task_id="task_0004",
                strategy="fill_existing",
                target=space.locator,
                text=answer,
            )
        ],
        tmp_path,
    )
    reparsed = DocxAdapter().parse(output)
    block_text = "\n".join(block.text for block in reparsed.blocks)
    op = PlacementOp(
        op_id="op_0004",
        task_id="task_0004",
        strategy="fill_existing",
        target=space.locator,
        text=answer,
    )
    assert answer_text_present(op, block_text)


def test_no_answer_spaces_output_contains_multi_paragraph_answer(tmp_path: Path) -> None:
    from docna.detect.run import detect_from_adapter
    from docna.ir import Answer
    from docna.place.planner import plan_placements
    from docna.pipeline import _answer_text_present
    from tests.detect_helpers import rule_based_mock_provider
    from tests.placement_helpers import apply_ops

    path = ensure_realworld_fixture("no_answer_spaces.docx")
    adapter = DocxAdapter()
    ir = adapter.parse(path)
    detection = detect_from_adapter(ir, adapter, rule_based_mock_provider())
    task = next(t for t in detection.tasks if "government policy" in t.prompt_text.lower())
    long_answer = (
        "Government policy influences inflation primarily through monetary and fiscal tools. "
        "Tightening policy reduces excess demand.\n\n"
        "In summary, government policy acts as a lever to influence demand."
    )
    answers = [Answer(task_id=task.task_id, text=long_answer, confidence=0.95)]
    ops = plan_placements(ir, detection.tasks, answers)
    op = next(op for op in ops if op.task_id == task.task_id)
    assert op.strategy == "insert_below"
    output = apply_ops(path, [op], tmp_path)
    reparsed = adapter.parse(output)
    block_text = "\n".join(block.text for block in reparsed.blocks)
    assert _answer_text_present(op, block_text)
