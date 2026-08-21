"""Job orchestrator connecting parse, detect, answer, place, and write stages."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from docna.adapters.base import FormatAdapter
from docna.adapters.registry import get_adapter
from docna.ai.metrics import ProviderMetrics
from docna.ai.instrumented import InstrumentedAIProvider
from docna.answer.context import build_context_packs
from docna.answer.generate import generate_answers
from docna.answer.generation_config import GenerationConfig
from docna.ai.port import AIProvider
from docna.config import Settings
from docna.detect.run import detect_from_adapter
from docna.ingest import ValidationError, validate_upload
from docna.ir import DocumentIR, PlacementOp
from docna.pipeline_models import (
    JobStatus,
    PipelineError,
    PipelineResult,
    PlacementOpSummary,
)
from docna.place.answer_text import answer_text_present
from docna.place.planner import plan_placements
from docna.review import build_review_report
from docna.serializers import summarize_placement_ops
from docna.storage.jobs import JobPaths, JobStore

logger = logging.getLogger(__name__)


class PipelineFailure(Exception):
    """Raised when a pipeline stage fails fatally."""

    def __init__(self, stage: str, message: str, *, task_id: str | None = None) -> None:
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.task_id = task_id


def run_job(
    store: JobStore,
    paths: JobPaths,
    provider: AIProvider,
    *,
    settings: Settings,
) -> PipelineResult:
    """Run the full DocNA pipeline for one stored job."""
    warnings: list[str] = []
    errors: list[PipelineError] = []
    tasks = []
    answers = []
    placement_summaries: list[PlacementOpSummary] = []
    source_format = None
    source_hash = None
    output_path = None
    review_report_path = None

    try:
        store.update_status(paths.job_id, "processing")
        source_format = validate_upload(paths.original, max_file_size=settings.max_file_size)
        source_hash = hashlib.sha256(paths.original.read_bytes()).hexdigest()
        store.update_status(
            paths.job_id,
            "parsing",
            source_format=source_format,
            source_hash=source_hash,
        )

        adapter = get_adapter(source_format)
        work_copy = store.create_working_copy(paths)
        ir = _parse_document(adapter, work_copy)

        store.update_status(paths.job_id, "detecting")
        instrumented_provider, metrics = _instrument_provider(provider)
        detection = detect_from_adapter(ir, adapter, instrumented_provider)
        tasks = detection.tasks
        warnings.extend(detection.warnings)
        warnings.extend(ir.warnings)

        store.update_status(paths.job_id, "answering")
        context_packs = build_context_packs(ir, tasks)
        generation = generate_answers(
            context_packs,
            instrumented_provider,
            config=GenerationConfig(
                max_concurrency=settings.max_concurrency,
                batch_size=settings.answer_batch_size,
                metrics=metrics,
            ),
        )
        answers = generation.answers
        warnings.extend(generation.warnings)
        logger.info("Job %s AI metrics: %s", paths.job_id, metrics.to_dict())

        store.update_status(paths.job_id, "placing")
        placement_ops = plan_placements(ir, tasks, answers)
        placement_summaries = summarize_placement_ops(placement_ops)

        store.save_pipeline_artifacts(
            paths,
            tasks=tasks,
            answers=answers,
            placement_ops=placement_ops,
            generation_errors=generation.errors,
        )

        output_docx = _apply_placements(adapter, work_copy, placement_ops)
        final_output = store.finalize_output(paths, output_docx)

        store.update_status(paths.job_id, "validating")
        reparsed = adapter.parse(final_output)
        validation_warnings = _validate_expected_writes(placement_ops, reparsed)
        warnings.extend(validation_warnings)

        review = build_review_report(
            job_id=paths.job_id,
            status="completed",
            tasks=tasks,
            answers=answers,
            placement_ops=placement_summaries,
            generation_errors=generation.errors,
            pipeline_errors=errors,
            warnings=warnings,
        )
        review_report_path = str(paths.review)
        store.save_review(paths, review.model_dump(mode="json"))
        output_path = str(final_output)

        record = store.update_status(
            paths.job_id,
            "completed",
            warnings=warnings,
            errors=errors,
            output_ready=True,
        )
        store.sync_workspace_from_job(paths.job_id)
        from docna.workspace import count_items_remaining
        from docna.workspace_ops import mark_download_ready_without_edits

        if count_items_remaining(review) == 0:
            mark_download_ready_without_edits(store, paths)
        logger.info("Job %s completed", paths.job_id)
        return PipelineResult(
            job_id=paths.job_id,
            status=record.status,
            source_format=record.source_format,
            source_hash=record.source_hash,
            output_path=output_path,
            review_report_path=review_report_path,
            tasks=tasks,
            answers=answers,
            placement_operations=placement_summaries,
            warnings=warnings,
            errors=errors,
        )
    except ValidationError as exc:
        return _fail_job(
            store,
            paths,
            stage="validation",
            message=str(exc),
            warnings=warnings,
            errors=errors,
            tasks=tasks,
            answers=answers,
            placement_summaries=placement_summaries,
            source_format=source_format,
            source_hash=source_hash,
        )
    except PipelineFailure as exc:
        store.remove_partial_output(paths)
        errors.append(
            PipelineError(stage=exc.stage, message=exc.message, task_id=exc.task_id)
        )
        return _fail_job(
            store,
            paths,
            stage=exc.stage,
            message=exc.message,
            warnings=warnings,
            errors=errors,
            tasks=tasks,
            answers=answers,
            placement_summaries=placement_summaries,
            source_format=source_format,
            source_hash=source_hash,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s failed unexpectedly", paths.job_id)
        store.remove_partial_output(paths)
        errors.append(PipelineError(stage="processing", message=str(exc)))
        return _fail_job(
            store,
            paths,
            stage="processing",
            message=str(exc),
            warnings=warnings,
            errors=errors,
            tasks=tasks,
            answers=answers,
            placement_summaries=placement_summaries,
            source_format=source_format,
            source_hash=source_hash,
        )


def _parse_document(adapter: FormatAdapter, work_copy: Path) -> DocumentIR:
    try:
        return adapter.parse(work_copy)
    except Exception as exc:  # noqa: BLE001
        raise PipelineFailure("parsing", f"Failed to parse document: {exc}") from exc


def _apply_placements(
    adapter: FormatAdapter,
    work_copy: Path,
    placement_ops: list[PlacementOp],
) -> Path:
    try:
        return adapter.apply(work_copy, placement_ops)
    except Exception as exc:  # noqa: BLE001
        raise PipelineFailure("placing", f"Failed to apply placements: {exc}") from exc


def _validate_expected_writes(
    placement_ops: list[PlacementOp],
    reparsed: DocumentIR,
) -> list[str]:
    warnings: list[str] = []
    block_text = "\n".join(block.text for block in reparsed.blocks)
    failures: list[str] = []

    for op in placement_ops:
        if op.strategy == "skip" or not op.text.strip():
            continue
        if answer_text_present(op, block_text):
            continue
        failures.append(f"{op.op_id}:{op.task_id}")

    if failures:
        raise PipelineFailure(
            "validating",
            "Final validation failed: expected answers were not found in output",
        )
    return warnings


def _answer_text_present(op: PlacementOp, block_text: str) -> bool:
    """Backward-compatible alias for placement validation."""
    return answer_text_present(op, block_text)


def _fail_job(
    store: JobStore,
    paths: JobPaths,
    *,
    stage: str,
    message: str,
    warnings: list[str],
    errors: list[PipelineError],
    tasks,
    answers,
    placement_summaries: list[PlacementOpSummary],
    source_format: str | None,
    source_hash: str | None,
) -> PipelineResult:
    if not any(error.stage == stage and error.message == message for error in errors):
        errors.append(PipelineError(stage=stage, message=message))

    review = build_review_report(
        job_id=paths.job_id,
        status="failed",
        tasks=tasks,
        answers=answers,
        placement_ops=placement_summaries,
        generation_errors=[],
        pipeline_errors=errors,
        warnings=warnings,
    )
    store.save_review(paths, review.model_dump(mode="json"))

    record = store.update_status(
        paths.job_id,
        "failed",
        source_format=source_format,
        source_hash=source_hash,
        warnings=warnings,
        errors=errors,
        output_ready=False,
    )
    store.sync_workspace_from_job(paths.job_id)
    return PipelineResult(
        job_id=paths.job_id,
        status=record.status,
        source_format=record.source_format,
        source_hash=record.source_hash,
        output_path=None,
        review_report_path=str(paths.review) if paths.review.exists() else None,
        tasks=tasks,
        answers=answers,
        placement_operations=placement_summaries,
        warnings=warnings,
        errors=errors,
    )


def original_is_immutable(paths: JobPaths, *, before_hash: str) -> bool:
    """Return True when the stored original still matches ``before_hash``."""
    if not paths.original.exists():
        return False
    current = hashlib.sha256(paths.original.read_bytes()).hexdigest()
    return current == before_hash


def _instrument_provider(provider: AIProvider) -> tuple[AIProvider, ProviderMetrics]:
    if isinstance(provider, InstrumentedAIProvider):
        return provider, provider.metrics
    instrumented = InstrumentedAIProvider(provider)
    return instrumented, instrumented.metrics
