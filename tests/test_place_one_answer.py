"""Regression tests: one task → one answer, no stacked Answer: blocks."""

from __future__ import annotations

from docna.adapters.docx import DocxAdapter
from docna.ir import Answer, PlacementOp, Task
from docna.place.planner import plan_placements
from tests.placement_helpers import (
    apply_ops,
    ensure_placement_fixture,
    parse_placement_fixture,
    sha256_file,
)
from tests.realworld_helpers import ensure_realworld_fixture


def test_insert_below_does_not_add_answer_label(tmp_path) -> None:
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
    joined = "\n".join(block.text for block in reparsed.blocks)
    assert "OOP organizes code into objects." in joined
    assert "Answer:" not in joined


def test_fill_existing_preserves_explicit_answer_label(tmp_path) -> None:
    original = ensure_realworld_fixture("existing_answer_sections.docx")
    ir = DocxAdapter().parse(original)
    label_space = ir.answer_spaces[1]  # space_0002: empty "Answer:" label paragraph
    assert label_space.current_text.strip() == "Answer:"
    output = apply_ops(
        original,
        [
            PlacementOp(
                op_id="op_0001",
                task_id="task_0001",
                strategy="fill_existing",
                target=label_space.locator,
                text="Example response text.",
            )
        ],
        tmp_path,
    )
    reparsed = DocxAdapter().parse(output)
    answer_block = next(
        block for block in reparsed.blocks if "Example response text." in block.text
    )
    assert answer_block.text.startswith("Answer:")
    assert "Example response text." in answer_block.text


def test_shared_space_produces_sequential_answers_without_labels(tmp_path) -> None:
    original = ensure_placement_fixture("multi_segment_shared_space.docx")
    before = sha256_file(original)
    ir = parse_placement_fixture("multi_segment_shared_space.docx")
    paragraph = next(block for block in ir.blocks if "Describe your role." in block.text)
    space_id = ir.answer_spaces[0].space_id
    prompts = [
        "Describe your role.",
        "Explain your responsibilities.",
        "List your main achievements.",
    ]
    tasks = [
        Task(
            task_id=f"task_{index + 1:04d}",
            kind="question",
            prompt_text=prompt,
            context_block_ids=[paragraph.block_id],
            answer_space_id=space_id,
            confidence=0.9,
        )
        for index, prompt in enumerate(prompts)
    ]
    answers = [
        Answer(task_id=task.task_id, text=f"Response {index + 1}", confidence=0.9)
        for index, task in enumerate(tasks)
    ]

    ops = plan_placements(ir, tasks, answers)
    output = apply_ops(original, ops, tmp_path)
    reparsed = DocxAdapter().parse(output)
    texts = [block.text.strip() for block in reparsed.blocks if block.text.strip()]

    assert sha256_file(original) == before
    assert texts.count("Response 1") == 1
    assert texts.count("Response 2") == 1
    assert texts.count("Response 3") == 1
    assert "Answer:" not in "\n".join(texts)

    question_index = next(i for i, text in enumerate(texts) if "Describe your role." in text)
    response_indices = [i for i, text in enumerate(texts) if text.startswith("Response ")]
    assert len(response_indices) == 3
    assert question_index < response_indices[0] < response_indices[1] < response_indices[2]


def test_single_task_still_fills_existing_blank(tmp_path) -> None:
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
    reparsed = DocxAdapter().parse(output)
    assert any("Jane Doe" in block.text for block in reparsed.blocks)


def test_table_cell_fill_still_works(tmp_path) -> None:
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
                text="Paris",
            )
        ],
        tmp_path,
    )
    reparsed = DocxAdapter().parse(output)
    assert any("Paris" in block.text for block in reparsed.blocks)
