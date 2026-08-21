"""Phase 10 human review before download tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app, get_service, get_settings
from docna.config import Settings
from docna.review import PLACEMENT_LABELS, placement_label
from docna.serializers import contains_locator_payload
from docna.service import DocNAService
from tests.conftest import frontend_source_text, homepage_text
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


def _create_job(client: TestClient, fixture_name: str = "blank_run.docx") -> str:
    fixture = ensure_placement_fixture(fixture_name)
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": (fixture_name, handle, "application/octet-stream")},
        )
    assert created.status_code == 200
    return created.json()["job_id"]


def test_review_page_markup_is_present_in_frontend() -> None:
    source = frontend_source_text()
    assert "Review workspace" in source
    assert "Document preview" in source
    assert "Export document" in source
    assert "Back to documents" in source
    assert "Needs your input" in source
    assert "completed-panel" not in source
    assert "View Review" not in source


def test_review_page_renders_completed_job(client: TestClient) -> None:
    job_id = _create_job(client)
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"

    review = client.get(f"/jobs/{job_id}/review").json()
    assert review["status"] == "completed"
    assert "summary" in review
    assert review["summary"]["questions_detected"] >= 1


def test_answered_tasks_include_answer_text_and_labels(client: TestClient) -> None:
    job_id = _create_job(client, "placement_integration.docx")
    review = client.get(f"/jobs/{job_id}/review").json()
    assert review["answered"]
    answered = review["answered"][0]
    assert answered["answer_text"]
    assert answered["placement_label"] in PLACEMENT_LABELS.values()
    assert "fill_existing" not in answered["placement_label"]


def test_skipped_tasks_appear_in_review(client: TestClient) -> None:
    job_id = _create_job(client)
    review = client.get(f"/jobs/{job_id}/review").json()
    assert isinstance(review["skipped"], list)


def test_flagged_tasks_include_attention_reason(client: TestClient) -> None:
    job_id = _create_job(client, "placement_integration.docx")
    review = client.get(f"/jobs/{job_id}/review").json()
    if review["flagged"]:
        flagged = review["flagged"][0]
        assert flagged.get("attention_reason")
        assert flagged.get("needs_review") is True


def test_confidence_is_available_for_percentage_display(client: TestClient) -> None:
    job_id = _create_job(client)
    review = client.get(f"/jobs/{job_id}/review").json()
    answered = review["answered"][0]
    assert answered["answer_confidence"] is not None
    assert 0 <= answered["answer_confidence"] <= 1
    percent = round(answered["answer_confidence"] * 100)
    assert 0 <= percent <= 100


def test_placement_strategy_maps_to_human_readable_label() -> None:
    assert placement_label("fill_existing") == "Existing answer space"
    assert placement_label("insert_below") == "Inserted below question"
    assert placement_label("fill_cell") == "Table cell"
    assert placement_label("skip") == "Not placed"
    assert placement_label(None) == "Not placed"


def test_review_payload_never_contains_locator_payloads(client: TestClient) -> None:
    job_id = _create_job(client, "placement_integration.docx")
    review = client.get(f"/jobs/{job_id}/review").json()
    serialized = json.dumps(review)
    assert not contains_locator_payload(review)
    assert "body_index" not in serialized
    assert '"payload"' not in serialized
    assert "xpath" not in serialized
    assert not re.search(r"sk-[a-zA-Z0-9]{20,}", serialized)


def test_failed_job_review_stays_safe_without_internal_errors(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret provider stack trace")

    monkeypatch.setattr("docna.pipeline.detect_from_adapter", boom)
    job_id = _create_job(client)
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "failed"
    assert "secret provider" not in status["error_message"]

    review = client.get(f"/jobs/{job_id}/review").json()
    serialized = json.dumps(review)
    assert review["status"] == "failed"
    assert "secret provider" not in serialized
    assert "Traceback" not in serialized


def test_analyze_another_document_copy_is_present(client: TestClient) -> None:
    text = homepage_text(client)
    assert "Back to documents" in text


def test_download_still_works_after_review(client: TestClient) -> None:
    job_id = _create_job(client)
    review = client.get(f"/jobs/{job_id}/review")
    assert review.status_code == 200

    download = client.get(f"/jobs/{job_id}/download")
    assert download.status_code == 200
    assert download.content.startswith(b"PK")


def test_frontend_js_shows_review_after_completion() -> None:
    source = frontend_source_text()
    assert "loadReview" in source
    assert 'setView("review")' in source
    assert "completed-panel" not in source
