"""Structured models for pipeline jobs and results."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from docna.ir import Answer, PlacementStrategy, SourceFormat, Task

JobStatus = Literal[
    "queued",
    "processing",
    "parsing",
    "detecting",
    "answering",
    "placing",
    "validating",
    "completed",
    "failed",
]


class PlacementOpSummary(BaseModel):
    """API-safe placement operation without locator payloads."""

    model_config = ConfigDict(extra="forbid")

    op_id: str
    task_id: str
    strategy: PlacementStrategy
    text: str = ""
    review_flags: list[str] = Field(default_factory=list)


class PipelineError(BaseModel):
    """Recorded pipeline failure."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    message: str
    task_id: str | None = None


class JobRecord(BaseModel):
    """Persisted job metadata."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: JobStatus
    source_format: SourceFormat | None = None
    source_hash: str | None = None
    original_filename: str | None = None
    created_at: datetime
    updated_at: datetime
    warnings: list[str] = Field(default_factory=list)
    errors: list[PipelineError] = Field(default_factory=list)
    output_ready: bool = False
    edited_output_ready: bool = False
    edited_task_ids: list[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    """Structured output from a completed or failed pipeline run."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(min_length=1)
    status: JobStatus
    source_format: SourceFormat | None = None
    source_hash: str | None = None
    output_path: str | None = None
    review_report_path: str | None = None
    tasks: list[Task] = Field(default_factory=list)
    answers: list[Answer] = Field(default_factory=list)
    placement_operations: list[PlacementOpSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[PipelineError] = Field(default_factory=list)


def utc_now() -> datetime:
    return datetime.now(UTC)
