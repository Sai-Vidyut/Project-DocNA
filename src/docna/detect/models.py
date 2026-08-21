"""Internal detection models. These are not part of the public IR contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from docna.ir import Task

SemanticKind = Literal[
    "question",
    "sub_question",
    "fill_blank",
    "table_item",
    "instruction",
    "narrative",
    "already_answered",
]

TASK_LIKE_KINDS = frozenset({"question", "sub_question", "fill_blank", "table_item"})


class SemanticClassificationItem(BaseModel):
    """One block classification returned by the semantic detector."""

    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(min_length=1)
    kind: SemanticKind
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class SemanticClassificationResponse(BaseModel):
    """Validated structured output from the semantic LLM pass."""

    model_config = ConfigDict(extra="forbid")

    classifications: list[SemanticClassificationItem] = Field(default_factory=list)


class StructuralCandidate(BaseModel):
    """Heuristic task candidate produced without an LLM."""

    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(min_length=1)
    provisional_kind: Literal[
        "question", "sub_question", "fill_blank", "table_item", "instruction"
    ]
    prompt_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    suggested_answer_space_id: str | None = None
    parent_block_id: str | None = None
    context_block_ids: list[str] = Field(default_factory=list)
    ambiguous_space: bool = False


class StructuralDetectionResult(BaseModel):
    """Output of the structural detection pass."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[StructuralCandidate] = Field(default_factory=list)
    instruction_candidates: list[StructuralCandidate] = Field(default_factory=list)
    excluded_blocks: dict[str, str] = Field(default_factory=dict)


class SemanticDetectionResult(BaseModel):
    """Output of the semantic classification pass."""

    model_config = ConfigDict(extra="forbid")

    classifications: list[SemanticClassificationItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DetectionResult(BaseModel):
    """Final merged detection output for downstream phases."""

    model_config = ConfigDict(extra="forbid")

    tasks: list[Task] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def answerable_tasks(self) -> list[Task]:
        return [
            task
            for task in self.tasks
            if task.kind in {"question", "sub_question", "fill_blank", "table_item"}
            and task.skip_reason is None
        ]

    @property
    def instruction_tasks(self) -> list[Task]:
        return [task for task in self.tasks if task.kind == "instruction"]
