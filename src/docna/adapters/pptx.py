"""PPTX adapter stub. Not implemented; registered so the format is explicit."""

from collections.abc import Sequence
from pathlib import Path

from docna.adapters.base import FormatAdapter
from docna.ir import DocumentIR, PlacementOp


class PptxAdapter(FormatAdapter):
    source_format = "pptx"

    def parse(self, path: Path) -> DocumentIR:
        raise NotImplementedError("PPTX support is not implemented")

    def apply(self, source_copy: Path, ops: Sequence[PlacementOp]) -> Path:
        raise NotImplementedError("PPTX support is not implemented")
