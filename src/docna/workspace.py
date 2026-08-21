"""User-facing workspace metadata layered on job storage."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from docna.answer.text import is_user_input_placeholder
from docna.pipeline_models import JobRecord, utc_now
from docna.review import ReviewReport, ReviewTaskEntry

WorkspaceStatus = Literal["processing", "needs_input", "ready", "needs_review", "failed"]
# user: created via app upload (POST /jobs) — shown in Documents/Home
# internal: tests, evaluation, direct JobStore — hidden from library listing
WorkspaceLibraryKind = Literal["user", "internal"]


class WorkspaceRecord(BaseModel):
    """Persisted workspace.json — internal record, not returned wholesale to clients."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    document_name: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    status: WorkspaceStatus
    questions_detected: int = Field(default=0, ge=0)
    answers_generated: int = Field(default=0, ge=0)
    items_remaining: int = Field(default=0, ge=0)
    items_needing_review: int = Field(default=0, ge=0)
    edited_task_ids: list[str] = Field(default_factory=list)
    export_filename: str = Field(default="", min_length=0)
    draft_edits: dict[str, str] = Field(default_factory=dict)
    download_ready: bool = False
    error_message: str | None = None
    library_kind: WorkspaceLibraryKind = "internal"


class WorkspaceSummary(BaseModel):
    """API-safe workspace metadata for list/detail responses."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    job_id: str
    document_name: str
    display_name: str
    created_at: datetime
    updated_at: datetime
    status: WorkspaceStatus
    questions_detected: int = Field(ge=0)
    answers_generated: int = Field(ge=0)
    items_remaining: int = Field(ge=0)
    items_needing_review: int = Field(ge=0)
    edited_task_ids: list[str] = Field(default_factory=list)
    export_filename: str
    download_ready: bool = False
    error_message: str | None = None


class WorkspaceRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=200)


class DraftAnswerEdit(BaseModel):
    """Draft or final answer text from the review UI."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    text: str = Field(max_length=50_000)


class WorkspaceEditsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edits: list[DraftAnswerEdit] = Field(default_factory=list)


def default_display_name(document_name: str) -> str:
    name = document_name.strip()
    if name.lower().endswith(".docx"):
        return name[:-5] or "Document"
    return name or "Document"


def default_export_filename(document_name: str) -> str:
    base = default_display_name(document_name)
    return f"{base}_completed.docx"


def count_items_remaining(review: ReviewReport) -> int:
    """Tasks that still require user input without a non-empty answer."""
    count = 0
    for entry in _iter_review_entries(review):
        if not entry.requires_user_input:
            continue
        if is_user_input_placeholder(entry.answer_text):
            count += 1
    return count


def derive_workspace_status(record: JobRecord, review: ReviewReport | None) -> WorkspaceStatus:
    if record.status == "failed":
        return "failed"
    if record.status != "completed":
        return "processing"
    if review is None:
        return "processing"

    remaining = count_items_remaining(review)
    if remaining > 0:
        return "needs_input"
    if review.summary.items_needing_review > 0:
        return "needs_review"
    if review.download_ready:
        return "ready"
    return "needs_review"


def is_user_library_workspace(record: WorkspaceRecord) -> bool:
    """True when the workspace should appear in Documents/Home."""
    return record.library_kind == "user"


def build_workspace_record(
    *,
    record: JobRecord,
    review: ReviewReport | None = None,
    draft_edits: dict[str, str] | None = None,
    display_name: str | None = None,
    library_kind: WorkspaceLibraryKind = "internal",
) -> WorkspaceRecord:
    document_name = record.original_filename or "document.docx"
    now = utc_now()
    merged_drafts = dict(draft_edits or ())

    questions_detected = 0
    answers_generated = 0
    items_needing_review = 0
    items_remaining = 0
    download_ready = False

    if review is not None:
        questions_detected = review.summary.questions_detected
        answers_generated = review.summary.answers_generated
        items_needing_review = review.summary.items_needing_review
        items_remaining = count_items_remaining(review)
        download_ready = review.download_ready

    status = derive_workspace_status(record, review)
    error_message = None
    if status == "failed" and record.errors:
        error_message = _safe_failure_message(record)

    return WorkspaceRecord(
        workspace_id=record.job_id,
        job_id=record.job_id,
        document_name=document_name,
        display_name=display_name or default_display_name(document_name),
        created_at=record.created_at,
        updated_at=record.updated_at,
        status=status,
        questions_detected=questions_detected,
        answers_generated=answers_generated,
        items_remaining=items_remaining,
        items_needing_review=items_needing_review,
        edited_task_ids=list(record.edited_task_ids),
        export_filename=default_export_filename(document_name),
        draft_edits=merged_drafts,
        download_ready=download_ready,
        error_message=error_message,
        library_kind=library_kind,
    )


def to_workspace_summary(record: WorkspaceRecord) -> WorkspaceSummary:
    return WorkspaceSummary(
        workspace_id=record.workspace_id,
        job_id=record.job_id,
        document_name=record.document_name,
        display_name=record.display_name,
        created_at=record.created_at,
        updated_at=record.updated_at,
        status=record.status,
        questions_detected=record.questions_detected,
        answers_generated=record.answers_generated,
        items_remaining=record.items_remaining,
        items_needing_review=record.items_needing_review,
        edited_task_ids=record.edited_task_ids,
        export_filename=record.export_filename,
        download_ready=record.download_ready,
        error_message=record.error_message,
    )


def merge_draft_edits_into_review(review: ReviewReport, draft_edits: dict[str, str]) -> ReviewReport:
    """Overlay unsaved draft text onto review entries for display/resume."""
    if not draft_edits:
        return review

    def patch(entries: list[ReviewTaskEntry]) -> list[ReviewTaskEntry]:
        patched: list[ReviewTaskEntry] = []
        for entry in entries:
            draft = draft_edits.get(entry.task_id)
            if draft is None:
                patched.append(entry)
                continue
            patched.append(entry.model_copy(update={"answer_text": draft}))
        return patched

    return review.model_copy(
        update={
            "answered": patch(review.answered),
            "skipped": patch(review.skipped),
            "flagged": patch(review.flagged),
        }
    )


def _iter_review_entries(review: ReviewReport):
    seen: set[str] = set()
    for source in (*review.answered, *review.skipped, *review.flagged):
        if source.task_id in seen:
            continue
        seen.add(source.task_id)
        yield source


def _safe_failure_message(record: JobRecord) -> str:
    if not record.errors:
        return "DocNA could not process this document."
    message = record.errors[0].message.lower()
    stage = record.errors[0].stage.lower()
    if "valid docx" in message or "not a valid docx" in message:
        return "Please make sure the file is a valid DOCX."
    if "unsupported file type" in message:
        return "DocNA supports DOCX files only."
    if "maximum size" in message:
        return "This file exceeds the maximum upload size."
    if stage == "validating" or "expected answers were not found" in message:
        return "DocNA could not verify all answers in the completed document."
    return "DocNA could not process this document."
