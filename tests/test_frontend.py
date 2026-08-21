"""Frontend static asset and service helper tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import FRONTEND_DIR, WEB_DIST, WEB_SRC, app, get_service, get_settings
from docna.config import Settings
from docna.pipeline_models import JobRecord, PipelineError, utc_now
from docna.service import DocNAService
from tests.conftest import frontend_source_text, homepage_text
from tests.pipeline_helpers import pipeline_mock_provider


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    return Settings.from_env(storage_dir=tmp_path / "jobs")


@pytest.fixture
def client(temp_settings: Settings) -> TestClient:
    service = DocNAService(temp_settings, provider=pipeline_mock_provider())
    app.dependency_overrides[get_settings] = lambda: temp_settings
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_frontend_assets_exist() -> None:
    assert WEB_SRC.is_dir()
    assert (WEB_DIST / "index.html").exists()
    assert any(WEB_DIST.glob("assets/*.js"))
    assert any(WEB_DIST.glob("assets/*.css"))


def test_homepage_serves_docna_ui(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    text = homepage_text(client)
    assert "DocNA" in text
    assert "Your workspace" in text


def test_frontend_assets_are_served(client: TestClient) -> None:
    html = client.get("/").text
    import re

    for pattern in (r'href="(/assets/[^"]+\.css)"', r'src="(/assets/[^"]+\.js)"'):
        match = re.search(pattern, html)
        assert match, f"Missing asset reference for {pattern}"
        response = client.get(match.group(1))
        assert response.status_code == 200
        assert response.text


def test_create_job_returns_queued_before_processing(client: TestClient) -> None:
    from tests.placement_helpers import ensure_placement_fixture

    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        response = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    status = client.get(f"/jobs/{payload['job_id']}").json()
    assert status["status"] == "completed"


def test_failed_job_includes_human_error_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("docna.pipeline.detect_from_adapter", boom)
    from tests.placement_helpers import ensure_placement_fixture

    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "failed"
    assert status["error_message"] == "DocNA could not process this document."
    assert "forced failure" not in status["error_message"]


def test_human_error_message_for_invalid_docx() -> None:
    record = JobRecord(
        job_id="job_test",
        status="failed",
        created_at=utc_now(),
        updated_at=utc_now(),
        errors=[PipelineError(stage="validation", message="File is not a valid DOCX document")],
    )
    message = DocNAService.human_error_message(record)
    assert message == "Please make sure the file is a valid DOCX."


def test_human_error_message_for_validation_failure() -> None:
    record = JobRecord(
        job_id="job_test",
        status="failed",
        created_at=utc_now(),
        updated_at=utc_now(),
        errors=[
            PipelineError(
                stage="validating",
                message="Final validation failed: expected answers were not found in output",
            )
        ],
    )
    message = DocNAService.human_error_message(record)
    assert message == "DocNA could not verify all answers in the completed document."


def test_frontend_distinguishes_documents_load_failure_from_empty_state() -> None:
    source = frontend_source_text()
    assert "loadFailed" in source
    assert "Couldn't load your documents." in source
    assert "Your workspace is empty" in source


def test_frontend_navigation_preserves_processing_job_context() -> None:
    source = frontend_source_text()
    assert "resumeProcessing" in source
    assert "fetchJobStatus" in source
    assert "startPolling" in source
    assert "persistActiveWorkspaceId" in source
    assert "clearReviewState" not in source


def test_frontend_documents_navigation_does_not_clear_backend_job() -> None:
    source = frontend_source_text()
    assert "goToDocuments" in source
    assert "stopPolling()" in source
    assert "loadDocuments()" in source

