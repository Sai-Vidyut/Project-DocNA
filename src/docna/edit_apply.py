"""Re-apply user-edited answers using persisted placement operations."""

from __future__ import annotations

import hashlib
import logging

from docna.adapters.registry import get_adapter
from docna.ir import Answer
from docna.pipeline import _apply_placements, _validate_expected_writes
from docna.review import build_review_report
from docna.review_edits import ReviewEditError, merge_edited_ops, validate_edits_for_job
from docna.serializers import summarize_placement_ops
from docna.storage.jobs import JobPaths, JobStore

logger = logging.getLogger(__name__)


def apply_edited_answers(
    store: JobStore,
    paths: JobPaths,
    *,
    edits,
) -> None:
    """Apply user-edited answers from the immutable original using stored placement ops."""
    record = store.load_record(paths.job_id)
    if record.status != "completed" or not record.output_ready:
        raise ReviewEditError("This document is not ready for edits.")

    if not store.has_pipeline_artifacts(paths):
        raise ReviewEditError("DocNA cannot apply edits for this document.")

    before_original_hash = hashlib.sha256(paths.original.read_bytes()).hexdigest()
    tasks = store.load_tasks(paths)
    answers = store.load_answers(paths)
    placement_ops = store.load_placement_ops(paths)
    generation_errors = store.load_generation_errors(paths)
    normalized_edits = validate_edits_for_job(
        tasks=tasks,
        placement_ops=placement_ops,
        edits=edits,
    )
    updated_ops = merge_edited_ops(placement_ops, normalized_edits)

    adapter = get_adapter(record.source_format or "docx")
    work_copy = store.create_working_copy(paths)

    try:
        produced = _apply_placements(adapter, work_copy, updated_ops)
        reparsed = adapter.parse(produced)
        _validate_expected_writes(updated_ops, reparsed)
        store.finalize_edited_output(paths, produced)
    except ReviewEditError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to apply edited answers for job %s", paths.job_id)
        raise ReviewEditError(
            "DocNA could not apply your edits. Your previous download is unchanged."
        ) from exc

    after_original_hash = hashlib.sha256(paths.original.read_bytes()).hexdigest()
    if before_original_hash != after_original_hash:
        logger.error("Original file mutated while applying edits for job %s", paths.job_id)
        store.remove_partial_edited_output(paths)
        raise ReviewEditError("DocNA could not apply your edits safely.")

    updated_answers = _merge_edited_answers(answers, normalized_edits)
    edited_task_ids = set(normalized_edits)
    if record.edited_task_ids:
        edited_task_ids |= set(record.edited_task_ids)

    placement_summaries = summarize_placement_ops(updated_ops)
    review = build_review_report(
        job_id=paths.job_id,
        status="completed",
        tasks=tasks,
        answers=updated_answers,
        placement_ops=placement_summaries,
        generation_errors=generation_errors,
        pipeline_errors=[],
        warnings=record.warnings,
        edited_task_ids=edited_task_ids,
        download_ready=True,
    )
    store.save_review(paths, review.model_dump(mode="json"))
    store.update_status(
        paths.job_id,
        "completed",
        edited_output_ready=True,
        edited_task_ids=sorted(edited_task_ids),
    )
    store.sync_workspace_from_job(paths.job_id)


def _merge_edited_answers(answers: list[Answer], edits: dict[str, str]) -> list[Answer]:
    merged: list[Answer] = []
    seen: set[str] = set()
    for answer in answers:
        if answer.task_id in edits:
            merged.append(answer.model_copy(update={"text": edits[answer.task_id]}))
        else:
            merged.append(answer)
        seen.add(answer.task_id)
    for task_id, text in edits.items():
        if task_id in seen:
            continue
        merged.append(Answer(task_id=task_id, text=text, confidence=1.0))
    return merged
