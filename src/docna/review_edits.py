"""Safe models and validation for user-edited review answers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from docna.ir import PlacementOp, Task
from docna.review import ANSWERABLE_KINDS

MAX_ANSWER_LENGTH = 50_000


class AnswerEdit(BaseModel):
    """One user-edited answer submitted from the review screen."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    text: str = Field(max_length=MAX_ANSWER_LENGTH)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Answer text cannot be empty.")
        return stripped


class ApplyEditsRequest(BaseModel):
    """Batch of answer edits for one completed job."""

    model_config = ConfigDict(extra="forbid")

    edits: list[AnswerEdit] = Field(default_factory=list)


class ReviewEditError(Exception):
    """Raised when submitted edits cannot be applied safely."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def editable_task_ids(tasks: Sequence[Task], placement_ops: Sequence[PlacementOp]) -> set[str]:
    """Return task ids that may receive user-edited answer text."""
    tasks_by_id = {task.task_id: task for task in tasks}
    editable: set[str] = set()
    for op in placement_ops:
        if op.strategy == "skip":
            continue
        task = tasks_by_id.get(op.task_id)
        if task is None:
            continue
        if task.kind not in ANSWERABLE_KINDS:
            continue
        if task.skip_reason is not None:
            continue
        editable.add(op.task_id)
    return editable


def validate_edits_for_job(
    *,
    tasks: Sequence[Task],
    placement_ops: Sequence[PlacementOp],
    edits: Sequence[AnswerEdit],
) -> dict[str, str]:
    """Validate edits belong to the job and return a task_id -> text map."""
    known_task_ids = {task.task_id for task in tasks}
    editable_ids = editable_task_ids(tasks, placement_ops)
    normalized: dict[str, str] = {}

    for edit in edits:
        if edit.task_id not in known_task_ids:
            raise ReviewEditError("One or more tasks are not part of this document.")
        if edit.task_id not in editable_ids:
            raise ReviewEditError("One or more tasks cannot be edited.")
        if edit.task_id in normalized:
            raise ReviewEditError("Duplicate task edits are not allowed.")
        normalized[edit.task_id] = edit.text

    return normalized


def merge_edited_ops(
    placement_ops: Sequence[PlacementOp],
    edits: Mapping[str, str],
) -> list[PlacementOp]:
    """Return placement ops with edited answer text substituted."""
    merged: list[PlacementOp] = []
    for op in placement_ops:
        if op.task_id in edits:
            merged.append(op.model_copy(update={"text": edits[op.task_id]}))
        else:
            merged.append(op)
    return merged
