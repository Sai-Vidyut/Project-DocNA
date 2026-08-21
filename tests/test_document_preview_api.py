"""Tests for document preview and task assistance APIs."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app, get_service, get_settings
from docna.config import Settings
from docna.service import DocNAService
from tests.pipeline_helpers import pipeline_mock_provider
from tests.placement_helpers import ensure_placement_fixture


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


def _upload_and_wait(client: TestClient) -> str:
    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"
    return job_id


def test_document_preview_endpoint(client: TestClient) -> None:
    job_id = _upload_and_wait(client)
    response = client.get(f"/jobs/{job_id}/preview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job_id
    assert payload["blocks"]
    assert "body_index" not in response.text
    assert "locator" not in response.text


def test_task_assist_endpoint(client: TestClient) -> None:
    job_id = _upload_and_wait(client)
    review = client.get(f"/jobs/{job_id}/review").json()
    task_id = review["answered"][0]["task_id"]
    response = client.post(
        f"/jobs/{job_id}/tasks/{task_id}/assist",
        json={"message": "What is this question asking?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"]
    assert "body_index" not in response.text


def test_review_includes_requires_user_input(client: TestClient) -> None:
    job_id = _upload_and_wait(client)
    review = client.get(f"/jobs/{job_id}/review").json()
    assert "requires_user_input" in review["answered"][0]
    assert "card_status" in review["answered"][0]
