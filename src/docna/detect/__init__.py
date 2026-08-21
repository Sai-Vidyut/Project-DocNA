"""Question detection: structural heuristics, semantic classification, and merge."""

from docna.detect.config import DetectionConfig
from docna.detect.merge import merge_detections
from docna.detect.models import DetectionResult
from docna.detect.run import detect_document_tasks, detect_from_adapter
from docna.detect.semantic import detect_semantic
from docna.detect.structural import detect_structural

__all__ = [
    "DetectionConfig",
    "DetectionResult",
    "detect_document_tasks",
    "detect_from_adapter",
    "detect_semantic",
    "detect_structural",
    "merge_detections",
]
