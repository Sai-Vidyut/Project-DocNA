"""High-level service used by the API and optional CLI."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from docna.ai.port import AIProvider
from docna.config import Settings
from docna.ingest import ValidationError, validate_upload
from docna.pipeline import run_job
from docna.pipeline_models import JobRecord, PipelineResult
from docna.storage.jobs import JobNotFoundError, JobStore
from docna.workspace import (
    WorkspaceRenameRequest,
    WorkspaceSummary,
    count_items_remaining,
    is_user_library_workspace,
    merge_draft_edits_into_review,
    to_workspace_summary,
)
from docna.workspace_ops import mark_download_ready_without_edits, persist_workspace_edits

logger = logging.getLogger(__name__)


class DocNAService:
    """Coordinates validation, storage, and pipeline execution."""

    def __init__(self, settings: Settings, *, provider: AIProvider | None = None) -> None:
        self.settings = settings
        self.store = JobStore(settings.storage_dir)
        self._provider = provider

    @property
    def provider(self) -> AIProvider:
        if self._provider is None:
            from docna.ai.factory import create_ai_provider

            self._provider = create_ai_provider(self.settings)
        return self._provider

    def create_job_from_upload(self, source_bytes: bytes, filename: str) -> str:
        """Validate and persist an uploaded DOCX. Returns the new job id."""
        temp_path = self._write_temp_upload(source_bytes, filename)
        try:
            validate_upload(temp_path, max_file_size=self.settings.max_file_size)
        except ValidationError:
            temp_path.unlink(missing_ok=True)
            raise
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

        paths = self.store.create_job(source_bytes, filename, library_kind="user")
        return paths.job_id

    def create_workspace_from_upload(self, source_bytes: bytes, filename: str) -> str:
        """Validate upload and create a persistent workspace. Returns workspace id."""
        return self.create_job_from_upload(source_bytes, filename)

    def process_job(self, job_id: str) -> PipelineResult:
        """Run the pipeline for a stored job."""
        paths = self.store.get_paths(job_id)
        before_hash = hashlib.sha256(paths.original.read_bytes()).hexdigest()
        result = run_job(self.store, paths, self.provider, settings=self.settings)
        after_hash = hashlib.sha256(paths.original.read_bytes()).hexdigest()
        if before_hash != after_hash:
            logger.error("Original file mutated for job %s", paths.job_id)
            raise RuntimeError("Original file was modified unexpectedly")
        return result

    def submit_upload(self, source_bytes: bytes, filename: str) -> tuple[str, str]:
        """Validate, store, and process an uploaded DOCX synchronously."""
        job_id = self.create_job_from_upload(source_bytes, filename)
        result = self.process_job(job_id)
        return job_id, result.status

    def get_job_status(self, job_id: str) -> dict:
        record = self.store.load_record(job_id)
        payload: dict[str, object] = {
            "job_id": record.job_id,
            "status": record.status,
            "warnings": record.warnings,
        }
        if record.original_filename:
            payload["original_filename"] = record.original_filename
        if record.status == "failed":
            payload["error_message"] = self.human_error_message(record)
        return payload

    @staticmethod
    def human_error_message(record: JobRecord) -> str:
        """Return a safe, user-facing failure message."""
        if record.errors:
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

    def get_review(self, job_id: str) -> dict:
        return self.store.load_review(job_id)

    def get_completed_output_path(self, job_id: str) -> Path:
        record = self.load_record(job_id)
        if record.status != "completed" or not record.output_ready:
            raise JobNotReadyError(f"Job {job_id} is not completed")
        paths = self.store.get_paths(job_id)
        if record.edited_output_ready and paths.edited_output_file.exists():
            return paths.edited_output_file
        if not paths.output_file.exists():
            raise JobNotReadyError(f"Completed output is not available for job {job_id}")
        return paths.output_file

    def apply_review_edits(self, job_id: str, request) -> dict[str, str]:
        """Validate and apply user-edited answers for a completed job."""
        from docna.edit_apply import apply_edited_answers
        from docna.review_edits import ReviewEditError

        paths = self.store.get_paths(job_id)
        try:
            apply_edited_answers(self.store, paths, edits=request.edits)
        except ReviewEditError as exc:
            raise ReviewEditValidationError(exc.message) from exc
        self.store.sync_workspace_from_job(job_id)
        return {"status": "ready", "message": "Your document is ready."}

    def list_workspaces(self) -> list[WorkspaceSummary]:
        summaries: list[WorkspaceSummary] = []
        for job_id in self.store.list_workspace_ids():
            try:
                workspace = self.store.sync_workspace_from_job(job_id)
                if not is_user_library_workspace(workspace):
                    continue
                summaries.append(to_workspace_summary(workspace))
            except JobNotFoundError:
                continue
            except Exception:  # noqa: BLE001
                logger.exception("Skipping workspace %s during list sync", job_id)
                continue
        summaries.sort(key=lambda item: item.updated_at, reverse=True)
        return summaries

    def get_workspace(self, workspace_id: str) -> WorkspaceSummary:
        workspace = self.store.sync_workspace_from_job(workspace_id)
        return to_workspace_summary(workspace)

    def rename_workspace(self, workspace_id: str, request: WorkspaceRenameRequest) -> WorkspaceSummary:
        workspace = self.store.load_workspace(workspace_id)
        display_name = request.display_name.strip()
        if not display_name:
            raise ReviewEditValidationError("Display name cannot be empty.")
        updated = workspace.model_copy(update={"display_name": display_name[:200]})
        paths = self.store.get_paths(workspace_id)
        self.store.save_workspace(updated, paths)
        return to_workspace_summary(updated)

    def delete_workspace(self, workspace_id: str) -> None:
        self.store.delete_job(workspace_id)

    def get_workspace_review(self, workspace_id: str) -> dict:
        from docna.review import ReviewReport

        paths = self.store.get_paths(workspace_id)
        record = self.load_record(workspace_id)
        if record.status != "completed" or not record.output_ready:
            raise JobNotReadyError(f"Workspace {workspace_id} is not ready for review")
        workspace = self.store.load_workspace(workspace_id)
        review = ReviewReport.model_validate(self.store.load_review(workspace_id))
        if workspace.draft_edits:
            review = merge_draft_edits_into_review(review, workspace.draft_edits)
        if count_items_remaining(review) == 0 and not review.download_ready:
            mark_download_ready_without_edits(self.store, paths)
            review = review.model_copy(update={"download_ready": True})
        return review.model_dump(mode="json")

    def apply_workspace_edits(self, workspace_id: str, request) -> dict[str, str]:
        paths = self.store.get_paths(workspace_id)
        workspace = self.store.load_workspace(workspace_id)
        persist_workspace_edits(self.store, paths, workspace, request.edits)
        return {"status": "saved", "message": "Changes saved."}

    def get_document_preview(self, job_id: str) -> dict:
        from docna.document_preview import build_document_preview
        from docna.review import ReviewReport

        record = self.load_record(job_id)
        if record.status != "completed" or not record.output_ready:
            raise JobNotReadyError(f"Job {job_id} is not completed")
        paths = self.store.get_paths(job_id)
        review = ReviewReport.model_validate(self.store.load_review(job_id))
        output_path = self.get_completed_output_path(job_id)
        preview = build_document_preview(
            job_id=job_id,
            output_path=output_path,
            review=review,
            filename=record.original_filename,
        )
        return preview.model_dump(mode="json")

    def assist_task(self, job_id: str, task_id: str, request) -> dict:
        from docna.task_assist import TaskAssistError, assist_with_task

        paths = self.store.get_paths(job_id)
        record = self.load_record(job_id)
        if record.status != "completed":
            raise JobNotReadyError(f"Job {job_id} is not completed")
        try:
            response = assist_with_task(
                store=self.store,
                paths=paths,
                provider=self.provider,
                task_id=task_id,
                request=request,
            )
        except TaskAssistError as exc:
            raise ReviewEditValidationError(exc.message) from exc
        return response.model_dump(mode="json")

    def load_record(self, job_id: str):
        return self.store.load_record(job_id)

    def process_file(self, source_path: Path) -> PipelineResult:
        """Run the same pipeline as the API for a local DOCX path."""
        source_bytes = source_path.read_bytes()
        paths = self.store.create_job(source_bytes, source_path.name)
        return run_job(self.store, paths, self.provider, settings=self.settings)

    def _write_temp_upload(self, source_bytes: bytes, filename: str) -> Path:
        suffix = Path(filename).suffix.lower() or ".docx"
        temp_dir = self.settings.storage_dir / "_uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"upload{suffix}"
        temp_path.write_bytes(source_bytes)
        return temp_path


class JobNotReadyError(Exception):
    """Raised when a download is requested before completion."""


class ReviewEditValidationError(Exception):
    """Raised when submitted review edits fail validation or apply."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
