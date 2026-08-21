"""API-safe serialization helpers."""

from __future__ import annotations

from collections.abc import Sequence

from docna.ir import PlacementOp
from docna.pipeline_models import PlacementOpSummary


def summarize_placement_ops(ops: Sequence[PlacementOp]) -> list[PlacementOpSummary]:
    """Convert placement operations to API-safe summaries without locators."""
    return [
        PlacementOpSummary(
            op_id=op.op_id,
            task_id=op.task_id,
            strategy=op.strategy,
            text=op.text,
            review_flags=list(op.review_flags),
        )
        for op in ops
    ]


def contains_locator_payload(value: object) -> bool:
    """Return True if a nested structure appears to expose locator payloads."""
    if isinstance(value, dict):
        if "payload" in value and "adapter" in value:
            return True
        return any(contains_locator_payload(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_locator_payload(item) for item in value)
    return False
