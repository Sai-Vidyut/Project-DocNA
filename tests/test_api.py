"""End-to-end pipeline and API integration tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app, get_service, get_settings
from docna.adapters.docx import DocxAdapter
from docna.config import Settings
from docna.serializers import contains_locator_payload
from docna.service import DocNAService
from tests.pipeline_helpers import pipeline_mock_provider
from tests.placement_helpers import ensure_placement_fixture, sha256_file


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


def test_end_to_end_pipeline_via_api(client: TestClient, service: DocNAService) -> None:
    fixture = ensure_placement_fixture("placement_integration.docx")
    before_hash = sha256_file(fixture)

    with fixture.open("rb") as handle:
        response = client.post(
            "/jobs",
            files={
                "file": (
                    "placement_integration.docx",
                    handle,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    payload = response.json()
    job_id = payload["job_id"]
    assert payload["status"] == "queued"

    status_response = client.get(f"/jobs/{job_id}")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "completed"
    assert not contains_locator_payload(status_payload)

    review_response = client.get(f"/jobs/{job_id}/review")
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["status"] == "completed"
    assert review["answered"]
    assert "summary" in review
    assert review["summary"]["answers_generated"] >= 1
    assert not contains_locator_payload(review)

    download_response = client.get(f"/jobs/{job_id}/download")
    assert download_response.status_code == 200
    output_bytes = download_response.content
    assert output_bytes.startswith(b"PK")

    paths = service.store.get_paths(job_id)
    assert sha256_file(paths.original) == before_hash

    reparsed = DocxAdapter().parse(paths.output_file)
    assert any("Answer for" in block.text for block in reparsed.blocks)


def test_successful_upload(client: TestClient) -> None:
    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        response = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert "job_id" in response.json()


@pytest.mark.parametrize(
    "filename",
    [".doc", ".docm", ".pdf", ".txt", ".md", ".pptx"],
)
def test_unsupported_extension(client: TestClient, filename: str) -> None:
    response = client.post(
        "/jobs",
        files={"file": (f"sample{filename}", b"dummy", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_malformed_docx(client: TestClient) -> None:
    response = client.post(
        "/jobs",
        files={"file": ("broken.docx", b"not-a-zip", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "valid DOCX" in response.json()["detail"]


def test_missing_job(client: TestClient) -> None:
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 404


def test_download_before_completion(client: TestClient, service: DocNAService) -> None:
    paths = service.store.create_job(b"placeholder", "pending.docx")
    service.store.update_status(paths.job_id, "processing")
    response = client.get(f"/jobs/{paths.job_id}/download")
    assert response.status_code == 409


def test_completed_download(client: TestClient) -> None:
    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    response = client.get(f"/jobs/{job_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_review_report(client: TestClient) -> None:
    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    response = client.get(f"/jobs/{job_id}/review")
    assert response.status_code == 200
    review = response.json()
    assert review["job_id"] == job_id
    assert "answered" in review
    assert "skipped" in review
    assert "flagged" in review


def test_file_size_limit(client: TestClient, temp_settings: Settings) -> None:
    small_settings = Settings(
        storage_dir=temp_settings.storage_dir,
        max_file_size=10,
        ai_provider="mock",
        max_concurrency=2,
        provider_chain=(),
    )
    app.dependency_overrides[get_settings] = lambda: small_settings
    app.dependency_overrides[get_service] = lambda: DocNAService(
        small_settings, provider=pipeline_mock_provider()
    )

    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        response = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    assert response.status_code == 400
    assert "maximum size" in response.json()["detail"]


def test_pipeline_failure_marks_job_failed(
    client: TestClient, service: DocNAService, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("docna.pipeline.detect_from_adapter", boom)
    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        response = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert response.json()["status"] == "queued"
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "failed"
    review = client.get(f"/jobs/{job_id}/review").json()
    assert review["status"] == "failed"


def test_original_immutability(client: TestClient, service: DocNAService) -> None:
    fixture = ensure_placement_fixture("placement_integration.docx")
    before = hashlib.sha256(fixture.read_bytes()).hexdigest()
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("placement_integration.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    paths = service.store.get_paths(job_id)
    after = hashlib.sha256(paths.original.read_bytes()).hexdigest()
    assert before == after


def test_review_has_no_locator_payloads(client: TestClient) -> None:
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
    assert "xpath" not in serialized
    assert '"payload"' not in serialized
