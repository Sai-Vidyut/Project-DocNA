"""DOCX adapter package. Parse is Phase 2; apply is Phase 4."""

from collections.abc import Sequence
from pathlib import Path

from docna.adapters.base import FormatAdapter
from docna.adapters.docx.apply import apply as apply_docx
from docna.adapters.docx.parse import parse as parse_docx
from docna.adapters.docx.preview import render_preview
from docna.ir import DocumentIR, PlacementOp


class DocxAdapter(FormatAdapter):
    """DOCX port. Parsing is read-only; write-back is Phase 4."""

    source_format = "docx"

    def parse(self, path: Path) -> DocumentIR:
        return parse_docx(path)

    def apply(self, source_copy: Path, ops: Sequence[PlacementOp]) -> Path:
        return apply_docx(source_copy, ops)

    def preview_text(self, ir: DocumentIR) -> str:
        return render_preview(ir)
