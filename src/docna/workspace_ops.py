"""Workspace edit persistence and review overlay helpers."""

from __future__ import annotations

from docna.edit_apply import apply_edited_answers
from docna.pipeline_models import utc_now
from docna.review import ReviewReport
from docna.review_edits import AnswerEdit, ReviewEditError, validate_edits_for_job
from docna.storage.jobs import JobPaths, JobStore
from docna.workspace import (
    DraftAnswerEdit,
    WorkspaceRecord,
    merge_draft_edits_into_review,
)


def apply_drafts_to_review_file(store: JobStore, paths: JobPaths, draft_edits: dict[str, str]) -> None:
    """Persist draft answer text into review.json for resume without regenerating DOCX."""
    if not paths.review.exists():
        return
    review = ReviewReport.model_validate_json(paths.review.read_text(encoding="utf-8"))
    merged = merge_draft_edits_into_review(review, draft_edits)
    store.save_review(paths, merged.model_dump(mode="json"))


def partition_workspace_edits(
    store: JobStore,
    paths: JobPaths,
    edits: list[DraftAnswerEdit],
) -> tuple[dict[str, str], list[AnswerEdit]]:
    """Split incoming edits into display drafts and apply-ready validated edits."""
    draft_updates: dict[str, str] = {edit.task_id: edit.text for edit in edits}
    apply_edits: list[AnswerEdit] = []

    if not edits or not store.has_pipeline_artifacts(paths):
        return draft_updates, apply_edits

    record = store.load_record(paths.job_id)
    if record.status != "completed" or not record.output_ready:
        return draft_updates, apply_edits

    tasks = store.load_tasks(paths)
    placement_ops = store.load_placement_ops(paths)
    answers = store.load_answers(paths)
    baseline = {answer.task_id: answer.text for answer in answers}

    candidates: list[AnswerEdit] = []
    for edit in edits:
        stripped = edit.text.strip()
        if not stripped:
            continue
        original = (baseline.get(edit.task_id) or "").strip()
        if stripped == original and edit.task_id not in record.edited_task_ids:
            continue
        try:
            candidates.append(AnswerEdit(task_id=edit.task_id, text=stripped))
        except ValueError:
            continue

    if not candidates:
        return draft_updates, apply_edits

    try:
        validate_edits_for_job(tasks=tasks, placement_ops=placement_ops, edits=candidates)
    except ReviewEditError:
        return draft_updates, apply_edits

    return draft_updates, candidates


def persist_workspace_edits(
    store: JobStore,
    paths: JobPaths,
    workspace: WorkspaceRecord,
    edits: list[DraftAnswerEdit],
) -> WorkspaceRecord:
    """Autosave drafts and apply validated edits using the existing edit pipeline."""
    draft_updates, apply_ready = partition_workspace_edits(store, paths, edits)

    merged_drafts = dict(workspace.draft_edits)
    merged_drafts.update(draft_updates)
    for edit in apply_ready:
        merged_drafts.pop(edit.task_id, None)

    apply_drafts_to_review_file(store, paths, merged_drafts)

    if apply_ready:
        apply_edited_answers(store, paths, edits=apply_ready)
    else:
        record = store.load_record(paths.job_id)
        store.save_record(record.model_copy(update={"updated_at": utc_now()}))
        interim = workspace.model_copy(
            update={"draft_edits": merged_drafts, "updated_at": utc_now()}
        )
        store.save_workspace(interim, paths)

    return store.sync_workspace_from_job(paths.job_id, preserve_drafts=True)


def mark_download_ready_without_edits(store: JobStore, paths: JobPaths) -> None:
    """Mark review export-ready when no user edits are required."""
    if not paths.review.exists():
        return
    review = ReviewReport.model_validate_json(paths.review.read_text(encoding="utf-8"))
    if review.download_ready:
        return
    review = review.model_copy(update={"download_ready": True})
    store.save_review(paths, review.model_dump(mode="json"))
    store.sync_workspace_from_job(paths.job_id)
