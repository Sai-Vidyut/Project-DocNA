"""Placement planner integration tests."""

from __future__ import annotations

from docna.adapters.docx import DocxAdapter
from docna.detect.run import detect_from_adapter
from docna.ir import Answer
from docna.place.planner import plan_placements
from tests.detect_helpers import rule_based_mock_provider
from tests.placement_helpers import parse_placement_fixture


def test_planner_produces_expected_strategies() -> None:
    ir = parse_placement_fixture("placement_integration.docx")
    adapter = DocxAdapter()
    detection = detect_from_adapter(ir, adapter, rule_based_mock_provider())
    answers = [
        Answer(task_id=task.task_id, text="Deterministic answer.", confidence=0.95)
        for task in detection.tasks
        if task.kind in {"question", "sub_question", "fill_blank", "table_item"}
        and task.skip_reason is None
    ]
    ops = plan_placements(ir, detection.tasks, answers)
    strategies = {op.strategy for op in ops}
    assert "skip" in strategies
    assert strategies.intersection({"fill_existing", "insert_below", "fill_cell"})
