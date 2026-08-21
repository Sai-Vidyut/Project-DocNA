"""Placement safety policy. Format-agnostic; never inspects locator payloads."""

from __future__ import annotations

from dataclasses import dataclass

from docna.ir import Answer, AnswerSpace, Block, PlacementOp, PlacementStrategy, Task
from docna.place.config import PlacementConfig

ANSWERABLE_KINDS = frozenset({"question", "sub_question", "fill_blank", "table_item"})


@dataclass(frozen=True, slots=True)
class PlacementDecision:
    """Intermediate policy result consumed by the planner."""

    strategy: PlacementStrategy
    target: object | None = None
    style_clone_from: object | None = None
    review_flags: tuple[str, ...] = ()
    skip_write: bool = False


def evaluate_placement(
    task: Task,
    answer: Answer | None,
    *,
    answer_space: AnswerSpace | None,
    question_block: Block | None,
    config: PlacementConfig,
    ambiguous_space: bool = False,
) -> PlacementDecision:
    """Decide how (or whether) to place an answer for one task."""
    flags: list[str] = []

    if task.kind == "instruction":
        return PlacementDecision(strategy="skip", review_flags=("instruction",))

    if task.skip_reason == "already_answered":
        return PlacementDecision(strategy="skip", review_flags=("already_answered",))

    if task.skip_reason == "low_confidence" or (
        task.confidence < config.confidence_threshold
    ):
        return PlacementDecision(strategy="skip", review_flags=("low_confidence",))

    if task.skip_reason == "review_recommended":
        flags.append("review_recommended")

    if answer is None or not answer.text.strip():
        return PlacementDecision(strategy="skip", review_flags=tuple(flags + ["no_answer"]))

    if answer_space is not None and _space_has_real_answer(answer_space):
        return PlacementDecision(strategy="skip", review_flags=("already_answered",))

    if ambiguous_space:
        flags.append("ambiguous_space")

    if answer_space is None:
        if question_block is None:
            return PlacementDecision(strategy="skip", review_flags=tuple(flags + ["no_target"]))
        return PlacementDecision(
            strategy="insert_below",
            target=question_block.locator,
            style_clone_from=question_block.locator,
            review_flags=tuple(flags),
        )

    if answer_space.type == "table_cell":
        return PlacementDecision(
            strategy="fill_cell",
            target=answer_space.locator,
            review_flags=tuple(flags),
        )

    if _answer_overflows_space(answer.text, answer_space, config):
        flags.append("overflow")
        if question_block is None:
            return PlacementDecision(strategy="skip", review_flags=tuple(flags + ["no_target"]))
        return PlacementDecision(
            strategy="insert_below",
            target=question_block.locator,
            style_clone_from=question_block.locator,
            review_flags=tuple(flags),
        )

    return PlacementDecision(
        strategy="fill_existing",
        target=answer_space.locator,
        style_clone_from=question_block.locator if question_block else answer_space.locator,
        review_flags=tuple(flags),
    )


def decision_to_op(
    *,
    op_id: str,
    task: Task,
    answer: Answer | None,
    decision: PlacementDecision,
) -> PlacementOp:
    """Convert a policy decision into a PlacementOp."""
    text = answer.text if answer is not None else ""
    if decision.strategy == "skip":
        return PlacementOp(
            op_id=op_id,
            task_id=task.task_id,
            strategy="skip",
            text=text,
            review_flags=list(decision.review_flags),
        )

    return PlacementOp(
        op_id=op_id,
        task_id=task.task_id,
        strategy=decision.strategy,
        target=decision.target,  # type: ignore[arg-type]
        text=text,
        style_clone_from=decision.style_clone_from,  # type: ignore[arg-type]
        review_flags=list(decision.review_flags),
    )


def _space_has_real_answer(space: AnswerSpace) -> bool:
    if space.is_placeholder:
        return False
    text = space.current_text.strip()
    if not text:
        return False
    if space.type == "none" and text.lower().startswith("answer"):
        return False
    return True


def _answer_overflows_space(text: str, space: AnswerSpace, config: PlacementConfig) -> bool:
    if space.type not in {"blank_run", "content_control"}:
        return False
    capacity = space.capacity_hint
    if capacity is None:
        capacity = len(space.current_text) if space.current_text else 0
    if capacity <= 0:
        return len(text.strip()) > 0
    return len(text) > int(capacity * config.overflow_ratio)
