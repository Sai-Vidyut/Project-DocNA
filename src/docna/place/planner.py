"""Deterministic placement planning. No LLM calls."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence

from docna.ir import Answer, DocumentIR, Block, PlacementOp, Task
from docna.place.config import PlacementConfig
from docna.place.policy import (
    ANSWERABLE_KINDS,
    PlacementDecision,
    decision_to_op,
    evaluate_placement,
)


def plan_placements(
    ir: DocumentIR,
    tasks: Sequence[Task],
    answers: Sequence[Answer],
    *,
    config: PlacementConfig | None = None,
) -> list[PlacementOp]:
    """Build placement operations from tasks, answers, and DocumentIR."""
    config = config or PlacementConfig()
    answers_by_task = {answer.task_id: answer for answer in answers}
    spaces_by_id = {space.space_id: space for space in ir.answer_spaces}
    block_by_id = {block.block_id: block for block in ir.blocks}
    ambiguous_spaces = _ambiguous_space_ids(ir)

    ops: list[PlacementOp] = []
    shared_spaces = _shared_answer_space_ids(tasks)
    chain_counters: dict[tuple[str, str], int] = defaultdict(int)
    for index, task in enumerate(tasks):
        if task.kind not in ANSWERABLE_KINDS and task.kind != "instruction":
            continue

        answer = answers_by_task.get(task.task_id)
        question_block = _task_block(ir, task, block_by_id)
        answer_space = (
            spaces_by_id.get(task.answer_space_id) if task.answer_space_id else None
        )
        ambiguous = bool(task.answer_space_id and task.answer_space_id in ambiguous_spaces)

        decision = evaluate_placement(
            task,
            answer,
            answer_space=answer_space,
            question_block=question_block,
            config=config,
            ambiguous_space=ambiguous,
        )
        decision = _resolve_shared_space_placement(
            decision,
            task=task,
            question_block=question_block,
            shared_spaces=shared_spaces,
            chain_counters=chain_counters,
        )

        ops.append(
            decision_to_op(
                op_id=f"op_{index + 1:04d}",
                task=task,
                answer=answer,
                decision=decision,
            )
        )

    return ops


def _shared_answer_space_ids(tasks: Sequence[Task]) -> set[str]:
    counts = Counter(task.answer_space_id for task in tasks if task.answer_space_id)
    return {space_id for space_id, count in counts.items() if count > 1}


def _resolve_shared_space_placement(
    decision: PlacementDecision,
    *,
    task: Task,
    question_block: Block | None,
    shared_spaces: set[str],
    chain_counters: dict[tuple[str, str], int],
) -> PlacementDecision:
    """Place each shared-space task in sequence; never stack answers in one blank."""
    if not task.answer_space_id or task.answer_space_id not in shared_spaces:
        return decision
    if question_block is None:
        return PlacementDecision(
            strategy="skip",
            review_flags=tuple([*decision.review_flags, "no_target"]),
        )

    flags = list(decision.review_flags)
    if "shared_answer_space" not in flags:
        flags.append("shared_answer_space")

    chain_key = (task.answer_space_id, question_block.block_id)
    chain_counters[chain_key] += 1
    if chain_counters[chain_key] > 1:
        flags.append("chain_insert")

    return PlacementDecision(
        strategy="insert_below",
        target=question_block.locator,
        style_clone_from=question_block.locator,
        review_flags=tuple(flags),
    )


def _task_block(
    ir: DocumentIR,
    task: Task,
    block_by_id: dict[str, Block],
) -> Block | None:
    prompt = task.prompt_text.strip()
    for block in ir.blocks:
        if block.text.strip() == prompt:
            return block
    for block_id in reversed(task.context_block_ids):
        block = block_by_id.get(block_id)
        if block is not None and block.text.strip() == prompt:
            return block
    for block_id in task.context_block_ids:
        block = block_by_id.get(block_id)
        if block is not None and prompt in block.text:
            return block
    for block in ir.blocks:
        if prompt in block.text:
            return block
    return None


def _ambiguous_space_ids(ir: DocumentIR) -> set[str]:
    locator_keys: dict[str, list[str]] = {}
    for space in ir.answer_spaces:
        key = f"{space.locator.adapter}:{id(space.locator)}"
        locator_keys.setdefault(key, []).append(space.space_id)

    block_to_spaces: dict[str, list[str]] = {}
    for task_space in ir.answer_spaces:
        for block in ir.blocks:
            if task_space.current_text and task_space.current_text in block.text:
                block_to_spaces.setdefault(block.block_id, []).append(task_space.space_id)

    ambiguous: set[str] = set()
    for spaces in block_to_spaces.values():
        if len(spaces) > 1:
            ambiguous.update(spaces)
    return ambiguous
