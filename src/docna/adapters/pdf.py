"""PDF adapter stub. Not implemented; registered so the format is explicit."""

from collections.abc import Sequence
from pathlib import Path

from docna.adapters.base import FormatAdapter
from docna.ir import DocumentIR, PlacementOp


class PdfAdapter(FormatAdapter):
    source_format = "pdf"

    def parse(self, path: Path) -> DocumentIR:
        raise NotImplementedError("PDF support is not implemented")

    def apply(self, source_copy: Path, ops: Sequence[PlacementOp]) -> Path:
        raise NotImplementedError("PDF support is not implemented")
