"""Phase 9 product validation regression tests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app, get_service, get_settings
from docna.adapters.docx import DocxAdapter
from docna.config import Settings
from docna.serializers import contains_locator_payload
from docna.service import DocNAService
from tests.conftest import homepage_text
from tests.pipeline_helpers import pipeline_mock_provider
from tests.placement_helpers import ensure_placement_fixture, sha256_file
from tests.realworld_helpers import ensure_realworld_fixture


@pytest.fixture
def temp_settings(tmp_path: Path) -> Settings:
    return Settings.from_env(storage_dir=tmp_path / "jobs")


@pytest.fixture
def service(temp_settings: Settings) -> DocNAService:
    return DocNAService(temp_settings, provider=pipeline_mock_provider())


@pytest.fixture
def client(service: DocNAService, temp_settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: temp_settings
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


USER_FLOW_FIXTURES = [
    ("school_college_questionnaire.docx", 1),
    ("blank_lines.docx", 1),
    ("no_answer_spaces.docx", 1),
    ("table_heavy_questionnaire.docx", 1),
    ("numbered_subquestions.docx", 1),
    ("multi_section_form.docx", 1),
]


@pytest.mark.parametrize("fixture_name,min_answered", USER_FLOW_FIXTURES)
def test_user_flow_fixture_completes_with_review_and_download(
    client: TestClient,
    service: DocNAService,
    fixture_name: str,
    min_answered: int,
) -> None:
    path = ensure_realworld_fixture(fixture_name)
    before = sha256_file(path)

    with path.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": (fixture_name, handle, "application/octet-stream")},
        )
    assert created.status_code == 200
    job_id = created.json()["job_id"]
    assert created.json()["status"] == "queued"

    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"
    assert status["original_filename"] == fixture_name
    assert not contains_locator_payload(status)

    review = client.get(f"/jobs/{job_id}/review").json()
    assert len(review["answered"]) >= min_answered
    assert "answered" in review and "skipped" in review and "flagged" in review
    assert not contains_locator_payload(review)

    download = client.get(f"/jobs/{job_id}/download")
    assert download.status_code == 200
    assert download.content.startswith(b"PK")

    paths = service.store.get_paths(job_id)
    assert sha256_file(paths.original) == before
    reparsed = DocxAdapter().parse(paths.output_file)
    assert reparsed.blocks


def test_homepage_communicates_docx_only_and_immutability(client: TestClient) -> None:
    text = homepage_text(client)
    assert "DOCX files only" in text
    assert "Your original document is never modified" in text
    assert "Review workspace" in text
    assert "Back to documents" in text


def test_api_errors_are_human_readable_without_stack_traces(client: TestClient) -> None:
    cases = [
        ("broken.docx", b"not-a-zip", "valid DOCX"),
        ("notes.pdf", b"%PDF-1.4", "Unsupported file type"),
        ("empty.docx", b"", "empty"),
    ]
    for filename, payload, expected in cases:
        response = client.post(
            "/jobs",
            files={"file": (filename, payload, "application/octet-stream")},
        )
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert expected.lower() in detail.lower()
        assert "Traceback" not in detail


def test_missing_job_and_download_before_completion(client: TestClient, service: DocNAService) -> None:
    missing = client.get("/jobs/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Job not found"

    paths = service.store.create_job(b"placeholder", "pending.docx")
    service.store.update_status(paths.job_id, "processing")
    blocked = client.get(f"/jobs/{paths.job_id}/download")
    assert blocked.status_code == 409


def test_failed_job_status_has_safe_error_message(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret internals")

    monkeypatch.setattr("docna.pipeline.detect_from_adapter", boom)

    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "failed"
    assert "error_message" in status
    assert "secret internals" not in status["error_message"]
    assert "Traceback" not in json.dumps(status)


def test_sensitive_paths_and_review_payloads_are_not_exposed(client: TestClient) -> None:
    fixture = ensure_placement_fixture("placement_integration.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("placement_integration.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    review = client.get(f"/jobs/{job_id}/review").json()
    serialized = json.dumps(review)
    assert "body_index" not in serialized
    assert '"payload"' not in serialized
    assert not re.search(r"sk-[a-zA-Z0-9]{20,}", serialized)

    assert client.get("/.env.local").status_code == 404
    assert client.get("/assets/../.env.local").status_code in {404, 400}
