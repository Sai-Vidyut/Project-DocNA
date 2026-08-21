"""Format-agnostic internal representation for DocNA.

Core modules (detect, answer, place, pipeline, ai) must operate only on these
models. Adapter-specific meaning lives in ``Locator.payload`` and is owned by
the format adapter that minted the locator. Core code must never inspect
payload contents.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceFormat = Literal["docx", "pdf", "txt", "md", "pptx"]
BlockKind = Literal["paragraph", "heading", "list_item", "table_cell", "textbox"]
RoleHint = Literal["body", "heading", "possible_question", "possible_blank"]
AnswerSpaceType = Literal[
    "blank_run",
    "empty_para",
    "content_control",
    "table_cell",
    "bookmark",
    "none",
]
TaskKind = Literal[
    "question",
    "sub_question",
    "fill_blank",
    "table_item",
    "instruction",
]
PlacementStrategy = Literal["fill_existing", "insert_below", "fill_cell", "skip"]

SOURCE_FORMATS: frozenset[str] = frozenset(("docx", "pdf", "txt", "md", "pptx"))


class _IRModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Locator(_IRModel):
    """Opaque handle to a location in a source document.

    ``payload`` is adapter-owned. Core code may pass locators through and
    compare them for equality. It must not branch on payload keys or values.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    adapter: str = Field(min_length=1)
    payload: dict[str, Any]


class Block(_IRModel):
    """An addressable reading unit in DocumentIR."""

    block_id: str = Field(min_length=1)
    kind: BlockKind
    text: str
    style_name: str | None = None
    list_level: int | None = None
    parent_block_id: str | None = None
    locator: Locator
    role_hint: RoleHint | None = None


class TableView(_IRModel):
    """Tabular region. Cell entries are block ids or cell text."""

    table_id: str = Field(min_length=1)
    rows: list[list[str]] = Field(default_factory=list)
    cell_locators: dict[tuple[int, int], Locator] = Field(default_factory=dict)
    header_row: bool = False


class AnswerSpace(_IRModel):
    """A location that may already exist for writing an answer."""

    space_id: str = Field(min_length=1)
    type: AnswerSpaceType
    locator: Locator
    current_text: str = ""
    is_placeholder: bool = False
    capacity_hint: int | None = None


class DocumentIR(_IRModel):
    """Canonical, format-agnostic view of a parsed document."""

    document_id: str = Field(min_length=1)
    source_format: SourceFormat
    source_hash: str = Field(min_length=1)
    blocks: list[Block] = Field(default_factory=list)
    tables: list[TableView] = Field(default_factory=list)
    outline: list[tuple[str, str]] = Field(default_factory=list)
    answer_spaces: list[AnswerSpace] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Task(_IRModel):
    """A detected question, blank, table item, or skipped instruction."""

    task_id: str = Field(min_length=1)
    kind: TaskKind
    prompt_text: str
    parent_task_id: str | None = None
    context_block_ids: list[str] = Field(default_factory=list)
    answer_space_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    skip_reason: str | None = None


class Answer(_IRModel):
    """Generated answer text for a single task."""

    task_id: str = Field(min_length=1)
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class PlacementOp(_IRModel):
    """A format-agnostic write instruction for an adapter to apply."""

    op_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    strategy: PlacementStrategy
    target: Locator | None = None
    text: str = ""
    style_clone_from: Locator | None = None
    review_flags: list[str] = Field(default_factory=list)
