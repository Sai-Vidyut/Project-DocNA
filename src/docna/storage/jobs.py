"""Job workspace layout. Original files stay immutable."""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from docna.answer.models import GenerationError
from docna.ir import Answer, PlacementOp, Task
from docna.pipeline_models import JobRecord, JobStatus, PipelineError, utc_now
from docna.review import ReviewReport
from docna.workspace import (
    WorkspaceLibraryKind,
    WorkspaceRecord,
    build_workspace_record,
    default_display_name,
)

logger = logging.getLogger(__name__)


class JobNotFoundError(FileNotFoundError):
    """Raised when a job directory or metadata file does not exist."""


@dataclass(frozen=True, slots=True)
class JobPaths:
    """Filesystem layout for one job."""

    job_id: str
    root: Path
    original: Path
    work: Path
    internal_dir: Path
    tasks_file: Path
    answers_file: Path
    placement_ops_file: Path
    generation_errors_file: Path
    output_dir: Path
    output_file: Path
    edited_output_file: Path
    review: Path
    metadata: Path
    workspace: Path


class JobStore:
    """Create and manage immutable job workspaces."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def create_job(
        self,
        source_bytes: bytes,
        original_filename: str,
        *,
        library_kind: WorkspaceLibraryKind = "internal",
    ) -> JobPaths:
        """Store the immutable original and initialize job metadata."""
        job_id = uuid.uuid4().hex
        paths = self._paths_for(job_id)
        paths.root.mkdir(parents=True)
        paths.original.parent.mkdir(parents=True)
        paths.work.mkdir(parents=True)
        paths.internal_dir.mkdir(parents=True)
        paths.output_dir.mkdir(parents=True)
        paths.original.write_bytes(source_bytes)

        now = utc_now()
        record = JobRecord(
            job_id=job_id,
            status="queued",
            original_filename=original_filename,
            created_at=now,
            updated_at=now,
        )
        self.save_record(record)
        self.save_workspace(
            build_workspace_record(
                record=record,
                display_name=default_display_name(original_filename),
                library_kind=library_kind,
            ),
            paths,
        )
        return paths

    def get_paths(self, job_id: str) -> JobPaths:
        paths = self._paths_for(job_id)
        if not paths.metadata.exists():
            raise JobNotFoundError(f"Job not found: {job_id}")
        return paths

    def load_record(self, job_id: str) -> JobRecord:
        paths = self.get_paths(job_id)
        return JobRecord.model_validate_json(paths.metadata.read_text(encoding="utf-8"))

    def save_record(self, record: JobRecord) -> None:
        paths = self._paths_for(record.job_id)
        paths.root.mkdir(parents=True, exist_ok=True)
        paths.metadata.write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        *,
        source_format: str | None = None,
        source_hash: str | None = None,
        warnings: list[str] | None = None,
        errors: list[PipelineError] | None = None,
        output_ready: bool | None = None,
        edited_output_ready: bool | None = None,
        edited_task_ids: list[str] | None = None,
    ) -> JobRecord:
        record = self.load_record(job_id)
        updates: dict[str, object] = {
            "status": status,
            "updated_at": utc_now(),
        }
        if source_format is not None:
            updates["source_format"] = source_format
        if source_hash is not None:
            updates["source_hash"] = source_hash
        if warnings is not None:
            updates["warnings"] = warnings
        if errors is not None:
            updates["errors"] = errors
        if output_ready is not None:
            updates["output_ready"] = output_ready
        if edited_output_ready is not None:
            updates["edited_output_ready"] = edited_output_ready
        if edited_task_ids is not None:
            updates["edited_task_ids"] = edited_task_ids
        record = record.model_copy(update=updates)
        self.save_record(record)
        return record

    def create_working_copy(self, paths: JobPaths) -> Path:
        """Copy the immutable original into the work directory."""
        work_copy = paths.work / "input.docx"
        shutil.copy2(paths.original, work_copy)
        return work_copy

    def save_review(self, paths: JobPaths, review_data: dict) -> None:
        paths.review.write_text(
            json.dumps(review_data, indent=2, default=str),
            encoding="utf-8",
        )

    def load_review(self, job_id: str) -> dict:
        paths = self.get_paths(job_id)
        if not paths.review.exists():
            raise FileNotFoundError("Review report is not available")
        return json.loads(paths.review.read_text(encoding="utf-8"))

    def save_pipeline_artifacts(
        self,
        paths: JobPaths,
        *,
        tasks: list[Task],
        answers: list[Answer],
        placement_ops: list[PlacementOp],
        generation_errors: list[GenerationError],
    ) -> None:
        """Persist internal pipeline artifacts needed for edit re-apply."""
        paths.internal_dir.mkdir(parents=True, exist_ok=True)
        paths.tasks_file.write_text(
            json.dumps([task.model_dump(mode="json") for task in tasks], indent=2),
            encoding="utf-8",
        )
        paths.answers_file.write_text(
            json.dumps([answer.model_dump(mode="json") for answer in answers], indent=2),
            encoding="utf-8",
        )
        paths.placement_ops_file.write_text(
            json.dumps([op.model_dump(mode="json") for op in placement_ops], indent=2),
            encoding="utf-8",
        )
        paths.generation_errors_file.write_text(
            json.dumps([error.model_dump(mode="json") for error in generation_errors], indent=2),
            encoding="utf-8",
        )

    def has_pipeline_artifacts(self, paths: JobPaths) -> bool:
        return (
            paths.tasks_file.exists()
            and paths.answers_file.exists()
            and paths.placement_ops_file.exists()
        )

    def load_tasks(self, paths: JobPaths) -> list[Task]:
        payload = json.loads(paths.tasks_file.read_text(encoding="utf-8"))
        return [Task.model_validate(item) for item in payload]

    def load_answers(self, paths: JobPaths) -> list[Answer]:
        payload = json.loads(paths.answers_file.read_text(encoding="utf-8"))
        return [Answer.model_validate(item) for item in payload]

    def load_placement_ops(self, paths: JobPaths) -> list[PlacementOp]:
        payload = json.loads(paths.placement_ops_file.read_text(encoding="utf-8"))
        return [PlacementOp.model_validate(item) for item in payload]

    def load_generation_errors(self, paths: JobPaths) -> list[GenerationError]:
        if not paths.generation_errors_file.exists():
            return []
        payload = json.loads(paths.generation_errors_file.read_text(encoding="utf-8"))
        return [GenerationError.model_validate(item) for item in payload]

    def finalize_output(self, paths: JobPaths, produced_path: Path) -> Path:
        """Move a completed DOCX into the output directory."""
        paths.output_dir.mkdir(parents=True, exist_ok=True)
        if produced_path.resolve() != paths.output_file.resolve():
            shutil.copy2(produced_path, paths.output_file)
        return paths.output_file

    def finalize_edited_output(self, paths: JobPaths, produced_path: Path) -> Path:
        """Atomically store the edited completed DOCX without touching the AI output."""
        paths.output_dir.mkdir(parents=True, exist_ok=True)
        temp_path = paths.edited_output_file.with_suffix(".tmp.docx")
        shutil.copy2(produced_path, temp_path)
        temp_path.replace(paths.edited_output_file)
        return paths.edited_output_file

    def remove_partial_output(self, paths: JobPaths) -> None:
        if paths.output_file.exists():
            paths.output_file.unlink()

    def remove_partial_edited_output(self, paths: JobPaths) -> None:
        temp_path = paths.edited_output_file.with_suffix(".tmp.docx")
        temp_path.unlink(missing_ok=True)

    def save_workspace(self, workspace: WorkspaceRecord, paths: JobPaths | None = None) -> None:
        target = paths or self.get_paths(workspace.job_id)
        target.root.mkdir(parents=True, exist_ok=True)
        target.workspace.write_text(
            workspace.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load_workspace(self, job_id: str) -> WorkspaceRecord:
        paths = self.get_paths(job_id)
        if paths.workspace.exists():
            return WorkspaceRecord.model_validate_json(paths.workspace.read_text(encoding="utf-8"))
        record = self.load_record(job_id)
        review = self._load_review_optional(paths)
        workspace = build_workspace_record(record=record, review=review)
        self.save_workspace(workspace, paths)
        return workspace

    def _load_review_optional(self, paths: JobPaths) -> ReviewReport | None:
        if not paths.review.exists():
            return None
        try:
            return ReviewReport.model_validate_json(paths.review.read_text(encoding="utf-8"))
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Ignoring invalid review.json for job %s: %s", paths.job_id, exc)
            return None

    def list_workspace_ids(self) -> list[str]:
        ids: list[str] = []
        if not self._root.exists():
            return ids
        for entry in self._root.iterdir():
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            if (entry / "job.json").exists():
                ids.append(entry.name)
        return ids

    def delete_job(self, job_id: str) -> None:
        paths = self.get_paths(job_id)
        shutil.rmtree(paths.root)

    def sync_workspace_from_job(self, job_id: str, *, preserve_drafts: bool = True) -> WorkspaceRecord:
        paths = self.get_paths(job_id)
        record = self.load_record(job_id)
        review = self._load_review_optional(paths)

        existing_drafts: dict[str, str] = {}
        display_name: str | None = None
        library_kind: WorkspaceLibraryKind = "internal"
        if paths.workspace.exists():
            try:
                existing = WorkspaceRecord.model_validate_json(paths.workspace.read_text(encoding="utf-8"))
                if preserve_drafts:
                    existing_drafts = dict(existing.draft_edits)
                display_name = existing.display_name
                library_kind = existing.library_kind
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                logger.warning("Rebuilding invalid workspace.json for job %s: %s", job_id, exc)

        workspace = build_workspace_record(
            record=record,
            review=review,
            draft_edits=existing_drafts,
            display_name=display_name,
            library_kind=library_kind,
        )
        self.save_workspace(workspace, paths)
        return workspace

    def _paths_for(self, job_id: str) -> JobPaths:
        root = self._root / job_id
        internal = root / "internal"
        return JobPaths(
            job_id=job_id,
            root=root,
            original=root / "original" / "input.docx",
            work=root / "work",
            internal_dir=internal,
            tasks_file=internal / "tasks.json",
            answers_file=internal / "answers.json",
            placement_ops_file=internal / "placement_ops.json",
            generation_errors_file=internal / "generation_errors.json",
            output_dir=root / "output",
            output_file=root / "output" / "completed.docx",
            edited_output_file=root / "output" / "edited.docx",
            review=root / "review.json",
            metadata=root / "job.json",
            workspace=root / "workspace.json",
        )
