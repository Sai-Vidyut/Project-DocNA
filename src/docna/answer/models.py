"""Structured models for answer context and generation results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from docna.ir import Answer


class NearbyBlock(BaseModel):
    """One neighboring block included as untrusted document context."""

    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(min_length=1)
    kind: str
    text: str


class TableContext(BaseModel):
    """Table-local context for a table_item task."""

    model_config = ConfigDict(extra="forbid")

    table_id: str = Field(min_length=1)
    row_index: int = Field(ge=0)
    col_index: int = Field(ge=0)
    row_label: str | None = None
    column_label: str | None = None
    cell_text: str = ""


class ContextPack(BaseModel):
    """Format-agnostic context sent to the answer-generation model."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    task_text: str
    task_kind: str
    section_title: str | None = None
    parent_question: str | None = None
    nearby_blocks: list[NearbyBlock] = Field(default_factory=list)
    table_context: TableContext | None = None
    document_instructions: list[str] = Field(default_factory=list)
    answer_space_capacity: int | None = None
    answer_mode: str | None = None


class AnswerGenerationItem(BaseModel):
    """Structured answer returned by the model for one task."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class AnswerGenerationResponse(BaseModel):
    """Provider response schema for a single answer-generation call."""

    model_config = ConfigDict(extra="forbid")

    answer: AnswerGenerationItem


class BatchAnswerGenerationResponse(BaseModel):
    """Provider response schema for a batched answer-generation call."""

    model_config = ConfigDict(extra="forbid")

    answers: list[AnswerGenerationItem] = Field(default_factory=list)


class GenerationError(BaseModel):
    """Explicit failure for one task without corrupting other answers."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    error_type: str
    message: str


class GenerationResult(BaseModel):
    """Batch answer-generation output."""

    model_config = ConfigDict(extra="forbid")

    answers: list[Answer] = Field(default_factory=list)
    errors: list[GenerationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
