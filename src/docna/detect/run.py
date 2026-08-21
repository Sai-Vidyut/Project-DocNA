"""Orchestrate hybrid structural + semantic detection."""

from __future__ import annotations

from docna.adapters.base import FormatAdapter
from docna.ai.port import AIProvider
from docna.detect.config import DetectionConfig
from docna.detect.merge import merge_detections
from docna.detect.models import DetectionResult
from docna.detect.semantic import detect_semantic
from docna.detect.structural import detect_structural
from docna.ir import DocumentIR


def detect_document_tasks(
    ir: DocumentIR,
    preview: str,
    provider: AIProvider,
    *,
    config: DetectionConfig | None = None,
) -> DetectionResult:
    """Run structural detection, semantic classification, and merge."""
    structural = detect_structural(ir)
    semantic = detect_semantic(ir, preview, provider, config=config)
    return merge_detections(ir, structural, semantic, config=config)


def detect_from_adapter(
    ir: DocumentIR,
    adapter: FormatAdapter,
    provider: AIProvider,
    *,
    config: DetectionConfig | None = None,
) -> DetectionResult:
    """Detect tasks using adapter preview text (no DOCX re-read)."""
    preview = adapter.preview_text(ir)
    return detect_document_tasks(ir, preview, provider, config=config)
