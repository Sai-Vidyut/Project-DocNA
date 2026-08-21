"""Format-agnostic adapter contract.

Adapters parse a source file into ``DocumentIR`` and apply ``PlacementOp``
values to a *working copy*. The original file must remain immutable. This
module contains no format-specific types (no OOXML, PDF objects, or similar).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from docna.ir import DocumentIR, PlacementOp, SourceFormat


class UnsupportedFormatError(ValueError):
    """Raised when the registry cannot resolve a source format."""


class FormatAdapter(ABC):
    """Port between a file format and the DocNA pipeline."""

    source_format: SourceFormat

    @abstractmethod
    def parse(self, path: Path) -> DocumentIR:
        """Parse ``path`` into DocumentIR, minting opaque locators."""

    @abstractmethod
    def apply(self, source_copy: Path, ops: Sequence[PlacementOp]) -> Path:
        """Apply placement ops to a working copy and return the output path.

        ``source_copy`` is never the user's original file. Implementations
        must not modify the original.
        """

    def preview_text(self, ir: DocumentIR) -> str:
        """Render a numbered, format-agnostic preview from DocumentIR.

        The default implementation uses only IR fields. Adapters may override
        it; they still must not leak format-specific markup into the preview.
        """
        lines: list[str] = []
        for block in ir.blocks:
            lines.append(f"[{block.block_id} {block.kind}] {block.text}")
        for table in ir.tables:
            for row_index, row in enumerate(table.rows):
                for col_index, cell in enumerate(row):
                    lines.append(
                        f"[{table.table_id} r{row_index}c{col_index}] {cell}"
                    )
        for space in ir.answer_spaces:
            lines.append(
                f"[{space.space_id} {space.type}] {space.current_text}"
            )
        return "\n".join(lines)
