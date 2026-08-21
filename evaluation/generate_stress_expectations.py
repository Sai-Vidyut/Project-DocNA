#!/usr/bin/env python3
"""Generate stress_expectations.json from mock baseline detection."""

from __future__ import annotations

import json
from pathlib import Path

from docna.adapters.docx import DocxAdapter
from docna.detect.run import detect_from_adapter
from tests.pipeline_helpers import pipeline_mock_provider
from tests.stress_helpers import ensure_all_stress_fixtures

EVAL_DIR = Path(__file__).resolve().parent
OUTPUT = EVAL_DIR / "stress_expectations.json"

MANUAL_OVERRIDES: dict[str, dict] = {
    "debate_worksheet.docx": {
        "must_detect": ["State your thesis", "supporting points", "counterargument"],
        "must_not_detect": ["Example thesis:"],
        "min_answerable_tasks": 3,
    },
    "volunteer_mixed_completion.docx": {
        "must_mark_already_answered": ["Volunteer ID", "Background check completed"],
        "min_answerable_tasks": 2,
    },
    "policy_partial_answers.docx": {
        "must_mark_already_answered": ["Have you read the code of conduct", "Date acknowledged"],
        "min_answerable_tasks": 2,
    },
    "memo_unstructured.docx": {
        "must_not_detect": ["For discussion only"],
        "min_answerable_tasks": 2,
    },
    "interview_no_blanks.docx": {
        "must_detect": [
            "complex project you led",
            "prioritize conflicting deadlines",
            "failure and what you learned",
        ],
        "min_answerable_tasks": 4,
    },
    "performance_review_runs.docx": {
        "must_detect": ["revenue target", "leadership initiatives", "measurable"],
        "min_answerable_tasks": 3,
    },
    "research_survey_dense.docx": {
        "must_detect": ["age range", "statistical software", "recruiting diverse"],
        "must_not_detect": ["Example response format"],
        "min_answerable_tasks": 3,
    },
}


def main() -> None:
    adapter = DocxAdapter()
    provider = pipeline_mock_provider()
    expectations: dict[str, dict] = {}

    for fixture_path in ensure_all_stress_fixtures():
        ir = adapter.parse(fixture_path)
        detection = detect_from_adapter(ir, adapter, provider)
        answerable = detection.answerable_tasks
        expectations[fixture_path.name] = {
            "description": fixture_path.stem.replace("_", " "),
            "mock_task_count": len(detection.tasks),
            "mock_answerable_count": len(answerable),
            "min_answerable_tasks": len(answerable),
            "must_detect": [task.prompt_text[:60] for task in answerable[:5]],
            "must_not_detect": [],
            "must_classify_instruction": [
                task.prompt_text[:80]
                for task in detection.tasks
                if task.kind == "instruction"
            ],
            "must_mark_already_answered": [
                task.prompt_text[:80]
                for task in detection.tasks
                if task.skip_reason == "already_answered"
            ],
        }
        if fixture_path.name in MANUAL_OVERRIDES:
            expectations[fixture_path.name].update(MANUAL_OVERRIDES[fixture_path.name])

    OUTPUT.write_text(json.dumps(expectations, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(expectations)} fixtures)")


if __name__ == "__main__":
    main()
