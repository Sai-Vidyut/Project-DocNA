"""Human-readable review report generation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from docna.answer.models import GenerationError
from docna.answer.text import is_user_input_placeholder, prepare_model_answer_text
from docna.ir import Answer, PlacementStrategy, Task
from docna.pipeline_models import JobStatus, PlacementOpSummary, PipelineError

ANSWERABLE_KINDS = frozenset({"question", "sub_question", "fill_blank", "table_item"})

PLACEMENT_LABELS: dict[PlacementStrategy | None, str] = {
    None: "Not placed",
    "fill_existing": "Existing answer space",
    "insert_below": "Inserted below question",
    "fill_cell": "Table cell",
    "skip": "Not placed",
}


class ReviewSummary(BaseModel):
    """High-level counts for the human review screen."""

    model_config = ConfigDict(extra="forbid")

    questions_detected: int = Field(ge=0)
    answers_generated: int = Field(ge=0)
    items_skipped: int = Field(ge=0)
    items_needing_review: int = Field(ge=0)


class ReviewTaskEntry(BaseModel):
    """One task row in the review report."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    task_text: str
    task_kind: str
    answer_status: str
    answer_text: str | None = None
    answer_confidence: float | None = None
    placement_strategy: PlacementStrategy | None = None
    placement_label: str = "Not placed"
    review_flags: list[str] = Field(default_factory=list)
    skip_reason: str | None = None
    attention_reason: str | None = None
    needs_review: bool = False
    editable: bool = False
    edited: bool = False
    answer_source: Literal["ai", "user"] = "ai"
    requires_user_input: bool = False
    card_status: str | None = None


class ReviewReport(BaseModel):
    """Persisted review.json payload."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: JobStatus
    summary: ReviewSummary
    answered: list[ReviewTaskEntry] = Field(default_factory=list)
    skipped: list[ReviewTaskEntry] = Field(default_factory=list)
    flagged: list[ReviewTaskEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    download_ready: bool = False


def build_review_report(
    *,
    job_id: str,
    status: JobStatus,
    tasks: Sequence[Task],
    answers: Sequence[Answer],
    placement_ops: Sequence[PlacementOpSummary],
    generation_errors: Sequence[GenerationError],
    pipeline_errors: Sequence[PipelineError],
    warnings: Sequence[str],
    edited_task_ids: set[str] | frozenset[str] | None = None,
    download_ready: bool = False,
) -> ReviewReport:
    """Build a review report from pipeline outputs."""
    edited_ids = set(edited_task_ids or ())
    answers_by_task = {answer.task_id: answer for answer in answers}
    ops_by_task = {op.task_id: op for op in placement_ops}
    generation_errors_by_task = {error.task_id: error for error in generation_errors}

    answered: list[ReviewTaskEntry] = []
    skipped: list[ReviewTaskEntry] = []
    flagged: list[ReviewTaskEntry] = []

    for task in tasks:
        answer = answers_by_task.get(task.task_id)
        op = ops_by_task.get(task.task_id)
        generation_error = generation_errors_by_task.get(task.task_id)
        entry = _build_entry(task, answer, op, generation_error, edited_ids)

        if generation_error is not None or (
            op is not None and op.strategy == "skip" and "no_answer" in op.review_flags
        ):
            skipped.append(entry)
        elif op is not None and op.review_flags:
            flagged.append(entry)
            if op.strategy != "skip":
                answered.append(entry)
        elif op is not None and op.strategy != "skip":
            answered.append(entry)
        else:
            skipped.append(entry)

    summary = ReviewSummary(
        questions_detected=_count_questions_detected(tasks),
        answers_generated=sum(1 for entry in answered if entry.answer_text),
        items_skipped=len(skipped),
        items_needing_review=_count_needing_review(answered, skipped, flagged),
    )

    safe_warnings = list(warnings)
    if pipeline_errors:
        safe_warnings.append(
            "DocNA encountered a processing problem. Some answers may be incomplete."
        )

    return ReviewReport(
        job_id=job_id,
        status=status,
        summary=summary,
        answered=answered,
        skipped=skipped,
        flagged=flagged,
        warnings=safe_warnings,
        download_ready=download_ready,
    )


def _build_entry(
    task: Task,
    answer: Answer | None,
    op: PlacementOpSummary | None,
    generation_error: GenerationError | None,
    edited_task_ids: set[str],
) -> ReviewTaskEntry:
    strategy = op.strategy if op is not None else None
    answer_text = _answer_text(answer, op)
    attention_reason = _attention_reason(task, answer, op, generation_error)
    editable = _is_editable(task, op, answer_text)
    edited = task.task_id in edited_task_ids
    if edited and answer_text is not None:
        answer_source: Literal["ai", "user"] = "user"
    else:
        answer_source = "ai"
    needs_review = attention_reason is not None and (
        generation_error is not None
        or (op is not None and bool(op.review_flags))
        or (answer is not None and answer.confidence < 0.90)
        or task.skip_reason not in {None, "already_answered"}
    )
    requires_user_input = _requires_user_input(task, answer_text, generation_error, op)
    card_status = _card_status(task, answer_text, requires_user_input, op, generation_error)
    return ReviewTaskEntry(
        task_id=task.task_id,
        task_text=task.prompt_text,
        task_kind=task.kind,
        answer_status=_answer_status(task, answer, generation_error, op),
        answer_text=answer_text,
        answer_confidence=answer.confidence if answer is not None else None,
        placement_strategy=strategy,
        placement_label=placement_label(strategy),
        review_flags=list(op.review_flags) if op is not None else [],
        skip_reason=task.skip_reason,
        attention_reason=attention_reason,
        needs_review=needs_review,
        editable=editable,
        edited=edited,
        answer_source=answer_source,
        requires_user_input=requires_user_input,
        card_status=card_status,
    )


def _is_editable(
    task: Task,
    op: PlacementOpSummary | None,
    answer_text: str | None,
) -> bool:
    if op is None or op.strategy == "skip" or answer_text is None:
        return False
    if task.kind not in ANSWERABLE_KINDS:
        return False
    return task.skip_reason is None


def _answer_text(answer: Answer | None, op: PlacementOpSummary | None) -> str | None:
    if answer is not None and answer.text.strip():
        return prepare_model_answer_text(answer.text)
    if op is not None and op.text.strip() and op.strategy != "skip":
        return prepare_model_answer_text(op.text)
    return None


def placement_label(strategy: PlacementStrategy | None) -> str:
    return PLACEMENT_LABELS.get(strategy, "Not placed")


def _count_questions_detected(tasks: Sequence[Task]) -> int:
    return sum(
        1
        for task in tasks
        if task.kind in ANSWERABLE_KINDS and task.skip_reason != "already_answered"
    )


def _count_needing_review(
    answered: Sequence[ReviewTaskEntry],
    skipped: Sequence[ReviewTaskEntry],
    flagged: Sequence[ReviewTaskEntry],
) -> int:
    task_ids: set[str] = set()
    for entries in (flagged, answered, skipped):
        for entry in entries:
            if entry.needs_review:
                task_ids.add(entry.task_id)
    return len(task_ids)


def _attention_reason(
    task: Task,
    answer: Answer | None,
    op: PlacementOpSummary | None,
    generation_error: GenerationError | None,
) -> str | None:
    if generation_error is not None:
        return "DocNA could not generate an answer."

    flags = op.review_flags if op is not None else []
    if "ambiguous_space" in flags:
        return "No suitable answer space was found."
    if "overflow" in flags:
        return "The answer may not fit the available space."
    if answer is not None and answer.confidence < 0.70:
        return "DocNA is not confident in this answer."
    if "review_recommended" in flags or (
        answer is not None and 0.70 <= answer.confidence < 0.90
    ):
        return "Review recommended before downloading."
    if task.skip_reason == "instruction" or "instruction" in flags:
        return "This is an instruction, not a question."
    if task.skip_reason == "already_answered":
        return "This item was already answered in the document."
    if op is not None and op.strategy == "skip" and "no_answer" in flags:
        return "DocNA could not generate an answer."
    if answer is None and task.kind in ANSWERABLE_KINDS and task.skip_reason is None:
        return "DocNA could not generate an answer."
    return None


def _requires_user_input(
    task: Task,
    answer_text: str | None,
    generation_error: GenerationError | None,
    op: PlacementOpSummary | None = None,
) -> bool:
    if generation_error is not None:
        return True
    if task.kind not in ANSWERABLE_KINDS:
        return False
    if task.skip_reason == "already_answered":
        return False
    if task.skip_reason not in {None, "review_recommended"}:
        return False
    # Placement failed without a user-personal placeholder — needs review, not user input.
    if op is not None and op.strategy == "skip":
        flags = set(op.review_flags)
        if "no_answer" not in flags and ("ambiguous_space" in flags or "overflow" in flags):
            return False
    text = (answer_text or "").strip()
    if is_user_input_placeholder(text):
        return True
    return False


def _card_status(
    task: Task,
    answer_text: str | None,
    requires_user_input: bool,
    op: PlacementOpSummary | None = None,
    generation_error: GenerationError | None = None,
) -> str | None:
    if not requires_user_input:
        if op is not None and op.strategy == "skip" and generation_error is None:
            flags = set(op.review_flags)
            if "ambiguous_space" in flags or "overflow" in flags:
                return "placement_review"
        return None
    text = (answer_text or "").strip()
    if is_user_input_placeholder(text) or text.startswith("[Your response"):
        lowered = task.prompt_text.lower()
        if any(
            token in lowered
            for token in (
                "name",
                "date",
                "reg.",
                "branch",
                "your family",
                "you notice",
                "give you happiness",
                "make you feel unhappy",
                "your view",
                "around you",
            )
        ):
            return "personal_response"
        return "needs_your_input"
    return "needs_review"


def _answer_status(
    task: Task,
    answer: Answer | None,
    generation_error: object | None,
    op: PlacementOpSummary | None,
) -> str:
    if generation_error is not None:
        return "generation_failed"
    if task.skip_reason:
        return f"skipped:{task.skip_reason}"
    if answer is None:
        return "no_answer"
    if op is None:
        return "planned"
    if op.strategy == "skip":
        if op.review_flags:
            return f"skipped:{op.review_flags[0]}"
        return "skipped"
    return "answered"
