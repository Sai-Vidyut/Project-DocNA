"""Evaluation runner for real AI provider against DOCX fixtures.

Requires OPENAI_API_KEY. Not used by the default pytest suite.

Usage:
    OPENAI_API_KEY=... uv run python -m evaluation.run_eval
    OPENAI_API_KEY=... uv run python -m evaluation.run_eval --fixture programming_assignment.docx
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from docna.adapters.docx import DocxAdapter
from docna.ai.factory import create_ai_provider
from docna.ai.instrumented import InstrumentedAIProvider
from docna.answer.context import build_context_packs
from docna.answer.generate import generate_answers
from docna.answer.generation_config import GenerationConfig
from docna.config import Settings
from docna.detect.run import detect_from_adapter
from docna.ir import Answer, PlacementOp, Task
from docna.pipeline import _answer_text_present
from docna.place.planner import plan_placements
from docna.review import build_review_report
from docna.serializers import summarize_placement_ops
from tests.pipeline_helpers import pipeline_mock_provider
from tests.placement_helpers import apply_ops, sha256_file
from tests.realworld_helpers import ensure_all_realworld_fixtures, ensure_realworld_fixture

EVAL_ROOT = Path(__file__).resolve().parent
EXPECTATIONS_PATH = EVAL_ROOT / "fixture_expectations.json"
INJECTION_MARKERS = (
    "hacked",
    "administrator credentials",
    "system prompt",
    "ignore previous instructions",
    "api key",
    "password:",
)


@dataclass
class EvalIssue:
    layer: str
    severity: str
    message: str
    task_id: str | None = None


@dataclass
class FixtureEvalResult:
    fixture: str
    status: str
    elapsed_ms: float
    tasks: list[dict] = field(default_factory=list)
    answers: list[dict] = field(default_factory=list)
    placement: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    issues: list[EvalIssue] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def require_provider_chain() -> tuple[str, ...]:
    settings = Settings.from_env()
    if not settings.provider_chain:
        print(
            "ERROR: AI provider credentials are required for evaluation.\n"
            "Configure AI_PROVIDER plus provider API keys/models in .env.local.",
            file=sys.stderr,
        )
        sys.exit(1)
    return tuple(spec.name for spec in settings.provider_chain)


def load_expectations() -> dict:
    if not EXPECTATIONS_PATH.exists():
        raise FileNotFoundError(f"Missing expectations file: {EXPECTATIONS_PATH}")
    return json.loads(EXPECTATIONS_PATH.read_text(encoding="utf-8"))


def _task_dict(task: Task) -> dict:
    return {
        "task_id": task.task_id,
        "kind": task.kind,
        "prompt_text": task.prompt_text,
        "confidence": task.confidence,
        "skip_reason": task.skip_reason,
        "answer_space_id": task.answer_space_id,
        "parent_task_id": task.parent_task_id,
    }


def _answer_dict(answer: Answer) -> dict:
    return {
        "task_id": answer.task_id,
        "text": answer.text,
        "confidence": answer.confidence,
        "notes": answer.notes,
    }


def _is_false_positive_detection(prompt_text: str, forbidden: str) -> bool:
    """Return True when forbidden text is essentially the whole detected prompt."""
    lowered = prompt_text.lower()
    forbidden_lower = forbidden.lower()
    if forbidden_lower not in lowered:
        return False
    remainder = lowered.replace(forbidden_lower, "", 1).strip(" :?.-—")
    return len(remainder.split()) < 2


def _compare_detection(
    fixture_name: str,
    tasks: list[Task],
    expectations: dict,
    mock_tasks: list[Task],
) -> list[EvalIssue]:
    issues: list[EvalIssue] = []
    spec = expectations.get(fixture_name, {})
    detected_texts = [task.prompt_text for task in tasks]
    mock_texts = [task.prompt_text for task in mock_tasks]

    for substring in spec.get("must_detect", []):
        if not any(substring.lower() in text.lower() for text in detected_texts):
            issues.append(
                EvalIssue(
                    layer="detection",
                    severity="error",
                    message=f"Expected prompt containing {substring!r} was not detected",
                )
            )

    for substring in spec.get("must_not_detect", []):
        matches = [
            text
            for text in detected_texts
            if _is_false_positive_detection(text, substring)
        ]
        if matches:
            issues.append(
                EvalIssue(
                    layer="detection",
                    severity="error",
                    message=f"False positive containing {substring!r}: {matches[0][:80]}",
                )
            )

    for substring in spec.get("must_classify_instruction", []):
        matched = [
            task
            for task in tasks
            if substring.lower() in task.prompt_text.lower() and task.kind != "instruction"
        ]
        if matched:
            issues.append(
                EvalIssue(
                    layer="detection",
                    severity="warning",
                    message=f"Instruction misclassified as {matched[0].kind}: {matched[0].prompt_text[:80]}",
                    task_id=matched[0].task_id,
                )
            )

    for substring in spec.get("must_mark_already_answered", []):
        matched = [
            task
            for task in tasks
            if substring.lower() in task.prompt_text.lower()
            and task.skip_reason != "already_answered"
            and task.kind != "instruction"
        ]
        if matched:
            issues.append(
                EvalIssue(
                    layer="detection",
                    severity="warning",
                    message=f"Already-answered item not skipped: {matched[0].prompt_text[:80]}",
                    task_id=matched[0].task_id,
                )
            )

    min_questions = spec.get("min_answerable_tasks")
    if min_questions is not None:
        answerable = [
            task
            for task in tasks
            if task.kind in {"question", "sub_question", "fill_blank", "table_item"}
            and task.skip_reason is None
        ]
        if len(answerable) < min_questions:
            issues.append(
                EvalIssue(
                    layer="detection",
                    severity="error",
                    message=(
                        f"Only {len(answerable)} answerable tasks detected; "
                        f"expected at least {min_questions}"
                    ),
                )
            )

    for mock_text in mock_texts:
        if not any(mock_text.strip() == text.strip() for text in detected_texts):
            if any(key in mock_text.lower() for key in ("example:", "thesis:", "ignore the system")):
                continue
            issues.append(
                EvalIssue(
                    layer="detection",
                    severity="info",
                    message=f"Mock-detected task missing from real AI run: {mock_text[:80]}",
                )
            )

    return issues


def _check_answers(answers: list[Answer], tasks: list[Task]) -> list[EvalIssue]:
    issues: list[EvalIssue] = []
    answers_by_task = {answer.task_id: answer for answer in answers}

    for task in tasks:
        if task.kind == "instruction" or task.skip_reason == "already_answered":
            continue
        if task.skip_reason == "low_confidence":
            continue
        answer = answers_by_task.get(task.task_id)
        if answer is None and task.kind in {"question", "sub_question", "fill_blank", "table_item"}:
            issues.append(
                EvalIssue(
                    layer="answer",
                    severity="error",
                    message="No answer generated for answerable task",
                    task_id=task.task_id,
                )
            )
            continue
        if answer is None:
            continue
        if not answer.text.strip():
            issues.append(
                EvalIssue(
                    layer="answer",
                    severity="error",
                    message="Empty answer text",
                    task_id=task.task_id,
                )
            )
        lowered = answer.text.lower()
        for marker in INJECTION_MARKERS:
            if marker in lowered and marker not in task.prompt_text.lower():
                issues.append(
                    EvalIssue(
                        layer="answer",
                        severity="error",
                        message=f"Answer appears to follow injection marker {marker!r}",
                        task_id=task.task_id,
                    )
                )

    return issues


def _check_placement(
    ops: list[PlacementOp],
    reparsed,
    answers: list[Answer],
) -> list[EvalIssue]:
    issues: list[EvalIssue] = []
    block_text = "\n".join(block.text for block in reparsed.blocks)
    answers_by_task = {answer.task_id: answer for answer in answers}

    for op in ops:
        if op.strategy == "skip":
            continue
        answer = answers_by_task.get(op.task_id)
        if answer is None:
            continue
        if not _answer_text_present(op, block_text):
            issues.append(
                EvalIssue(
                    layer="placement",
                    severity="error",
                    message=f"Expected answer not found in output for strategy {op.strategy}",
                    task_id=op.task_id,
                )
            )
    return issues


def evaluate_fixture(
    fixture_path: Path,
    provider: InstrumentedAIProvider,
    expectations: dict,
    output_dir: Path,
    *,
    settings: Settings,
) -> FixtureEvalResult:
    started = time.perf_counter()
    adapter = DocxAdapter()
    issues: list[EvalIssue] = []
    warnings: list[str] = []

    fixture_dir = output_dir / fixture_path.stem
    fixture_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fixture_path, fixture_dir / "input.docx")

    ir = adapter.parse(fixture_path)
    warnings.extend(ir.warnings)

    mock_detection = detect_from_adapter(ir, adapter, pipeline_mock_provider())
    detection = detect_from_adapter(ir, adapter, provider)
    tasks = detection.tasks
    warnings.extend(detection.warnings)

    issues.extend(
        _compare_detection(fixture_path.name, tasks, expectations, mock_detection.tasks)
    )

    packs = build_context_packs(ir, tasks)
    if not packs and any(
        task.kind in {"question", "sub_question", "fill_blank", "table_item"}
        and task.skip_reason is None
        for task in tasks
    ):
        issues.append(
            EvalIssue(
                layer="context",
                severity="error",
                message="Answerable tasks detected but no context packs built",
            )
        )

    generation = generate_answers(
        packs,
        provider,
        config=GenerationConfig(
            max_concurrency=settings.max_concurrency,
            batch_size=settings.answer_batch_size,
        ),
    )
    answers = generation.answers
    warnings.extend(generation.warnings)
    for error in generation.errors:
        issues.append(
            EvalIssue(
                layer="answer",
                severity="error",
                message=f"{error.error_type}: {error.message}",
                task_id=error.task_id,
            )
        )
    issues.extend(_check_answers(answers, tasks))

    ops = plan_placements(ir, tasks, answers)
    summaries = summarize_placement_ops(ops)
    status = "completed"

    try:
        work_dir = fixture_dir / "work"
        work_dir.mkdir(exist_ok=True)
        output_path = apply_ops(fixture_path, ops, work_dir)
        shutil.copy2(output_path, fixture_dir / "output.docx")
        reparsed = adapter.parse(output_path)
        issues.extend(_check_placement(ops, reparsed, answers))
    except Exception as exc:  # noqa: BLE001
        status = "failed"
        issues.append(
            EvalIssue(
                layer="pipeline",
                severity="error",
                message=str(exc),
            )
        )
        reparsed = None

    review = build_review_report(
        job_id=fixture_path.stem,
        status="completed" if status == "completed" else "failed",
        tasks=tasks,
        answers=answers,
        placement_ops=summaries,
        generation_errors=generation.errors,
        pipeline_errors=[],
        warnings=warnings,
    )

    detection_payload = {
        "tasks": [_task_dict(task) for task in tasks],
        "mock_baseline_tasks": [_task_dict(task) for task in mock_detection.tasks],
        "warnings": detection.warnings,
    }
    answers_payload = {
        "answers": [_answer_dict(answer) for answer in answers],
        "errors": [error.model_dump() for error in generation.errors],
        "warnings": generation.warnings,
    }
    review_payload = review.model_dump(mode="json")
    issues_payload = [asdict(issue) for issue in issues]

    (fixture_dir / "detection.json").write_text(
        json.dumps(detection_payload, indent=2), encoding="utf-8"
    )
    (fixture_dir / "answers.json").write_text(
        json.dumps(answers_payload, indent=2), encoding="utf-8"
    )
    (fixture_dir / "review.json").write_text(
        json.dumps(review_payload, indent=2), encoding="utf-8"
    )
    (fixture_dir / "issues.json").write_text(
        json.dumps(issues_payload, indent=2), encoding="utf-8"
    )

    elapsed_ms = (time.perf_counter() - started) * 1000
    if any(issue.severity == "error" for issue in issues):
        status = "failed"

    return FixtureEvalResult(
        fixture=fixture_path.name,
        status=status,
        elapsed_ms=elapsed_ms,
        tasks=[_task_dict(task) for task in tasks],
        answers=[_answer_dict(answer) for answer in answers],
        placement=[summary.model_dump() for summary in summaries],
        warnings=warnings,
        issues=issues,
        metrics=provider.metrics.to_dict(),
    )


def run_evaluation(
    *,
    fixtures: list[Path] | None = None,
    output_dir: Path | None = None,
) -> dict:
    base_settings = Settings.from_env(
        storage_dir=Path.cwd() / "evaluation" / "_scratch",
    )
    if not base_settings.provider_chain:
        require_provider_chain()

    settings = Settings(
        storage_dir=base_settings.storage_dir,
        max_file_size=base_settings.max_file_size,
        ai_provider=base_settings.ai_provider,
        max_concurrency=base_settings.max_concurrency,
        provider_chain=base_settings.provider_chain,
    )

    base_provider = create_ai_provider(settings)
    provider = InstrumentedAIProvider(base_provider)
    expectations = load_expectations()

    fixture_paths = fixtures or ensure_all_realworld_fixtures()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir or (EVAL_ROOT / f"run_{timestamp}")
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[FixtureEvalResult] = []
    for fixture_path in fixture_paths:
        print(f"Evaluating {fixture_path.name}...", flush=True)
        result = evaluate_fixture(
            fixture_path,
            provider,
            expectations,
            run_dir,
            settings=settings,
        )
        results.append(result)
        errors = sum(1 for issue in result.issues if issue.severity == "error")
        print(f"  status={result.status} issues={len(result.issues)} errors={errors}")

    summary = {
        "timestamp": timestamp,
        "provider": settings.ai_provider,
        "provider_chain": [spec.name for spec in settings.provider_chain],
        "fixtures_evaluated": len(results),
        "completed": sum(1 for result in results if result.status == "completed"),
        "failed": sum(1 for result in results if result.status == "failed"),
        "metrics": provider.metrics.to_dict(),
        "issue_counts": _issue_counts(results),
        "fixtures": [
            {
                "fixture": result.fixture,
                "status": result.status,
                "elapsed_ms": round(result.elapsed_ms, 2),
                "task_count": len(result.tasks),
                "answer_count": len(result.answers),
                "issues": [asdict(issue) for issue in result.issues],
            }
            for result in results
        ],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"run_dir": str(run_dir), "summary": summary}


def _issue_counts(results: list[FixtureEvalResult]) -> dict:
    counts: dict[str, int] = {}
    for result in results:
        for issue in result.issues:
            key = f"{issue.layer}:{issue.severity}"
            counts[key] = counts.get(key, 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DocNA real AI evaluation harness")
    parser.add_argument("--fixture", help="Evaluate a single fixture filename")
    parser.add_argument("--output-dir", type=Path, help="Override output directory")
    args = parser.parse_args()

    fixtures = None
    if args.fixture:
        fixtures = [ensure_realworld_fixture(args.fixture)]

    payload = run_evaluation(fixtures=fixtures, output_dir=args.output_dir)
    print(json.dumps(payload["summary"], indent=2))
    print(f"\nReport written to: {payload['run_dir']}")


if __name__ == "__main__":
    main()
