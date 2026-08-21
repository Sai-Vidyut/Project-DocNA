"""Phase 12 stress corpus regression tests (mock provider, no API keys)."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.api import app, get_service, get_settings
from docna.adapters.docx import DocxAdapter
from docna.config import Settings
from docna.pipeline import run_job
from docna.serializers import contains_locator_payload
from docna.service import DocNAService
from docna.storage.jobs import JobStore
from evaluation.run_stress import load_stress_expectations, run_stress_evaluation
from tests.pipeline_helpers import pipeline_mock_provider
from tests.placement_helpers import sha256_file
from tests.stress_helpers import STRESS_DIR, ensure_all_stress_fixtures, ensure_stress_fixture
from tests.validation_harness import run_fixture


@pytest.fixture(scope="session")
def stress_fixtures() -> list[Path]:
    return ensure_all_stress_fixtures()


@pytest.fixture
def job_store(tmp_path: Path) -> JobStore:
    return JobStore(tmp_path / "jobs")


def test_stress_corpus_has_eighteen_fixtures(stress_fixtures: list[Path]) -> None:
    assert len(stress_fixtures) == 18
    assert STRESS_DIR.exists()


def test_stress_expectations_cover_all_fixtures(stress_fixtures: list[Path]) -> None:
    expectations = load_stress_expectations()
    assert len(expectations) == 18
    for fixture in stress_fixtures:
        assert fixture.name in expectations


def test_all_stress_fixtures_complete_mock_pipeline_without_crash(
    stress_fixtures: list[Path], tmp_path: Path
) -> None:
    for fixture in stress_fixtures:
        report = run_fixture(fixture, tmp_path / fixture.stem)
        assert report.original_unchanged, fixture.name
        assert report.status == "completed", f"{fixture.name}: {report.errors}"
        if report.tasks_answerable > 0:
            assert report.output_opens, fixture.name
            assert not report.errors, f"{fixture.name}: {report.errors}"


def test_stress_fixtures_with_tasks_produce_valid_output(
    stress_fixtures: list[Path], tmp_path: Path
) -> None:
    for fixture in stress_fixtures:
        report = run_fixture(fixture, tmp_path / fixture.stem)
        if report.tasks_answerable == 0:
            continue
        assert report.output_valid_zip
        assert report.table_count_before == report.table_count_after


def test_stress_job_store_pipeline_preserves_original(
    job_store: JobStore, tmp_path: Path, stress_fixtures: list[Path]
) -> None:
    fixture = ensure_stress_fixture("grant_proposal_messy.docx")
    before = hashlib.sha256(fixture.read_bytes()).hexdigest()
    paths = job_store.create_job(fixture.read_bytes(), fixture.name)
    settings = Settings.from_env(storage_dir=tmp_path / "jobs")
    result = run_job(job_store, paths, pipeline_mock_provider(), settings=settings)
    after = hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert before == after
    assert result.status == "completed"
    assert zipfile.is_zipfile(paths.output_file)
    Document(paths.output_file)


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings.from_env(storage_dir=tmp_path / "jobs")
    service = DocNAService(settings, provider=pipeline_mock_provider())
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_stress_editable_review_flow(client: TestClient, tmp_path: Path) -> None:
    fixture = ensure_stress_fixture("budget_forecast_cells.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": (fixture.name, handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    review = client.get(f"/jobs/{job_id}/review").json()
    editable = [item for item in review["answered"] if item.get("editable")]
    assert len(editable) >= 2

    first = editable[0]
    second = editable[1]
    edited_one = "Stress edited answer one."
    edited_two = "Stress edited answer two."
    apply_one = client.post(
        f"/jobs/{job_id}/edits",
        json={"edits": [{"task_id": first["task_id"], "text": edited_one}]},
    )
    assert apply_one.status_code == 200

    before_original = sha256_file(fixture)
    apply_two = client.post(
        f"/jobs/{job_id}/edits",
        json={
            "edits": [
                {"task_id": first["task_id"], "text": edited_one},
                {"task_id": second["task_id"], "text": edited_two},
            ]
        },
    )
    assert apply_two.status_code == 200
    assert sha256_file(fixture) == before_original

    download = client.get(f"/jobs/{job_id}/download")
    assert download.status_code == 200
    output_path = tmp_path / "edited_download.docx"
    output_path.write_bytes(download.content)
    reparsed = DocxAdapter().parse(output_path)
    joined = "\n".join(block.text for block in reparsed.blocks)
    assert edited_two in joined
    assert not contains_locator_payload(review)


def test_stress_evaluation_harness_runs_mock_pass(tmp_path: Path) -> None:
    payload = run_stress_evaluation(
        fixtures=[ensure_stress_fixture("clinical_intake_merged.docx")],
        output_dir=tmp_path / "stress_run",
        use_real_ai=False,
        run_edit_checks=False,
    )
    summary = payload["summary"]
    assert summary["fixtures_evaluated"] == 1
    assert (tmp_path / "stress_run" / "summary.json").exists()
    assert (tmp_path / "stress_run" / "inspection_report.md").exists()


def test_stress_corpus_includes_formatting_and_table_variants(stress_fixtures: list[Path]) -> None:
    names = {path.name for path in stress_fixtures}
    assert "newsletter_with_header.docx" in names
    assert "clinical_intake_merged.docx" in names
    assert "budget_forecast_cells.docx" in names
    assert "hr_onboarding_underlines.docx" in names
    assert "course_syllabus_breaks.docx" in names
