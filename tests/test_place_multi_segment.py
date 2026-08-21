"""Regression tests for multi-segment tasks sharing one block/answer space."""

from __future__ import annotations

from docna.adapters.docx import DocxAdapter
from docna.ir import Answer, Task
from docna.pipeline import _validate_expected_writes
from docna.place.planner import plan_placements
from docna.place.answer_text import answer_text_present
from tests.placement_helpers import (
    apply_ops,
    ensure_placement_fixture,
    parse_placement_fixture,
    sha256_file,
)


def test_planner_uses_unique_strategies_for_shared_answer_space() -> None:
    ir = parse_placement_fixture("multi_segment_shared_space.docx")
    paragraph = next(
        block
        for block in ir.blocks
        if "Describe your role." in block.text and "Explain your responsibilities." in block.text
    )
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
        Answer(task_id=task.task_id, text=f"Answer for {task.prompt_text}", confidence=0.9)
        for task in tasks
    ]

    ops = plan_placements(ir, tasks, answers)
    active = [op for op in ops if op.strategy != "skip"]

    assert len(active) == 3
    assert all(op.strategy == "insert_below" for op in active)
    assert "shared_answer_space" in active[0].review_flags
    assert "chain_insert" not in active[0].review_flags
    assert "shared_answer_space" in active[1].review_flags
    assert "chain_insert" in active[1].review_flags
    assert "shared_answer_space" in active[2].review_flags
    assert "chain_insert" in active[2].review_flags


def test_task_block_prefers_segment_paragraph_over_neighbor_context() -> None:
    from docna.place.planner import _task_block

    ir = parse_placement_fixture("multi_segment_shared_space.docx")
    paragraph = next(
        block
        for block in ir.blocks
        if "Describe your role." in block.text and "Explain your responsibilities." in block.text
    )
    neighbor = next(block for block in ir.blocks if block.block_id != paragraph.block_id)
    block_by_id = {block.block_id: block for block in ir.blocks}
    task = Task(
        task_id="task_0002",
        kind="question",
        prompt_text="Explain your responsibilities.",
        context_block_ids=[neighbor.block_id, paragraph.block_id],
        confidence=0.9,
    )
    resolved = _task_block(ir, task, block_by_id)
    assert resolved is not None
    assert resolved.block_id == paragraph.block_id


def test_multi_segment_shared_space_passes_validation_and_preserves_original(
    tmp_path,
) -> None:
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
        Answer(
            task_id=task.task_id,
            text={
                "Describe your role.": "Teacher and mentor.",
                "Explain your responsibilities.": "Guide students and design curriculum.",
                "List your main achievements.": "Published two learning modules.",
            }[task.prompt_text],
            confidence=0.9,
        )
        for task in tasks
    ]

    ops = plan_placements(ir, tasks, answers)
    output = apply_ops(original, ops, tmp_path)
    reparsed = DocxAdapter().parse(output)
    block_text = "\n".join(block.text for block in reparsed.blocks)
    texts = [block.text for block in reparsed.blocks]

    for op in ops:
        if op.strategy == "skip" or not op.text.strip():
            continue
        assert answer_text_present(op, block_text)

    question_index = next(i for i, text in enumerate(texts) if "Describe your role." in text)
    answer_indices = [
        i
        for i, text in enumerate(texts)
        if text.strip()
        in {
            "Teacher and mentor.",
            "Guide students and design curriculum.",
            "Published two learning modules.",
        }
    ]
    assert len(answer_indices) == 3
    assert answer_indices == sorted(answer_indices)
    assert question_index < answer_indices[0] < answer_indices[1] < answer_indices[2]
    assert block_text.count("Answer:") == 0

    _validate_expected_writes(ops, reparsed)
    assert sha256_file(original) == before
