"""Pipeline orchestration unit tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from docna.adapters.docx import DocxAdapter
from docna.config import Settings
from docna.pipeline import run_job
from docna.storage.jobs import JobStore
from tests.pipeline_helpers import pipeline_mock_provider
from tests.placement_helpers import ensure_placement_fixture, sha256_file


@pytest.fixture
def job_store(tmp_path: Path) -> JobStore:
    return JobStore(tmp_path / "jobs")


def test_pipeline_completes_placement_integration(
    job_store: JobStore, tmp_path: Path
) -> None:
    fixture = ensure_placement_fixture("placement_integration.docx")
    before_hash = sha256_file(fixture)
    source_bytes = fixture.read_bytes()
    paths = job_store.create_job(source_bytes, fixture.name)
    settings = Settings.from_env(storage_dir=tmp_path / "jobs")

    result = run_job(
        job_store,
        paths,
        pipeline_mock_provider(),
        settings=settings,
    )

    assert result.status == "completed"
    assert result.output_path is not None
    assert result.review_report_path is not None
    assert result.tasks
    assert result.answers
    assert result.placement_operations
    assert sha256_file(paths.original) == before_hash
    assert paths.output_file.exists()
    assert paths.review.exists()

    reparsed = DocxAdapter().parse(paths.output_file)
    applied = [op for op in result.placement_operations if op.strategy != "skip"]
    for op in applied:
        assert any(op.text in block.text for block in reparsed.blocks)


def test_pipeline_failure_preserves_original(
    job_store: JobStore, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = ensure_placement_fixture("blank_run.docx")
    before_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
    paths = job_store.create_job(fixture.read_bytes(), fixture.name)
    settings = Settings.from_env(storage_dir=tmp_path / "jobs")

    def boom(*_args, **_kwargs):
        raise RuntimeError("detect failed")

    monkeypatch.setattr("docna.pipeline.detect_from_adapter", boom)
    result = run_job(
        job_store,
        paths,
        pipeline_mock_provider(),
        settings=settings,
    )

    assert result.status == "failed"
    assert not paths.output_file.exists()
    after_hash = hashlib.sha256(paths.original.read_bytes()).hexdigest()
    assert before_hash == after_hash
