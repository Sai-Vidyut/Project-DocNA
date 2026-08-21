"""Phase 14A persistent local workspace tests."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app, get_service, get_settings
from docna.config import Settings
from docna.serializers import contains_locator_payload
from docna.service import DocNAService
from tests.pipeline_helpers import pipeline_mock_provider
from tests.placement_helpers import ensure_placement_fixture


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


def _upload(client: TestClient, fixture_name: str = "blank_run.docx") -> str:
    fixture = ensure_placement_fixture(fixture_name)
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": (fixture_name, handle, "application/octet-stream")},
        )
    assert created.status_code == 200
    payload = created.json()
    assert "workspace_id" in payload
    job_id = payload["job_id"]
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"
    return job_id


def _first_editable_task(review: dict) -> dict:
    for item in review["answered"]:
        if item.get("editable"):
            return item
    raise AssertionError("No editable task found")


def test_workspace_created_after_upload(client: TestClient, temp_settings: Settings) -> None:
    job_id = _upload(client, "placement_integration.docx")
    workspace_path = temp_settings.storage_dir / job_id / "workspace.json"
    assert workspace_path.exists()
    workspace = json.loads(workspace_path.read_text(encoding="utf-8"))
    assert workspace["workspace_id"] == job_id
    assert workspace["job_id"] == job_id
    assert workspace["document_name"] == "placement_integration.docx"


def test_workspace_appears_in_list(client: TestClient) -> None:
    job_id = _upload(client)
    listed = client.get("/workspaces").json()
    ids = {item["workspace_id"] for item in listed["workspaces"]}
    assert job_id in ids


def test_workspaces_ordered_by_updated_at(client: TestClient) -> None:
    first = _upload(client, "blank_run.docx")
    time.sleep(0.01)
    second = _upload(client, "placement_integration.docx")
    listed = client.get("/workspaces").json()["workspaces"]
    assert listed[0]["workspace_id"] == second
    assert listed[1]["workspace_id"] == first


def test_workspace_metadata_is_safe(client: TestClient) -> None:
    job_id = _upload(client)
    detail = client.get(f"/workspaces/{job_id}").json()
    assert contains_locator_payload(detail) is False
    dumped = json.dumps(detail).lower()
    for token in ("block_locator", "placement_op", "api_key"):
        assert token not in dumped
    for key in detail:
        assert key in {
            "workspace_id",
            "job_id",
            "document_name",
            "display_name",
            "created_at",
            "updated_at",
            "status",
            "questions_detected",
            "answers_generated",
            "items_remaining",
            "items_needing_review",
            "edited_task_ids",
            "export_filename",
            "download_ready",
            "error_message",
        }


def test_workspace_can_be_reopened(client: TestClient) -> None:
    job_id = _upload(client, "placement_integration.docx")
    review = client.get(f"/workspaces/{job_id}/review").json()
    assert review["job_id"] == job_id
    assert review["status"] == "completed"


def test_existing_edits_survive_reopening(client: TestClient, service: DocNAService) -> None:
    job_id = _upload(client, "placement_integration.docx")
    review = client.get(f"/workspaces/{job_id}/review").json()
    task = _first_editable_task(review)
    edited = "Persisted workspace edit text."
    save = client.post(
        f"/workspaces/{job_id}/edits",
        json={"edits": [{"task_id": task["task_id"], "text": edited}]},
    )
    assert save.status_code == 200

    reopened = client.get(f"/workspaces/{job_id}/review").json()
    entry = next(item for item in reopened["answered"] if item["task_id"] == task["task_id"])
    assert entry["answer_text"] == edited

    paths = service.store.get_paths(job_id)
    assert paths.original.exists()
    assert paths.original.read_bytes()


def test_autosaved_draft_persists(client: TestClient) -> None:
    job_id = _upload(client, "placement_integration.docx")
    review = client.get(f"/workspaces/{job_id}/review").json()
    task = _first_editable_task(review)
    draft = "Partial draft answer"
    response = client.post(
        f"/workspaces/{job_id}/edits",
        json={"edits": [{"task_id": task["task_id"], "text": draft}]},
    )
    assert response.status_code == 200
    reopened = client.get(f"/workspaces/{job_id}/review").json()
    entry = next(item for item in reopened["answered"] if item["task_id"] == task["task_id"])
    assert entry["answer_text"] == draft


def test_ai_answer_unchanged_when_not_edited(client: TestClient) -> None:
    job_id = _upload(client, "placement_integration.docx")
    before = client.get(f"/workspaces/{job_id}/review").json()
    untouched = [
        item for item in before["answered"] if item.get("editable") and item.get("answer_text")
    ]
    assert untouched
    original_map = {item["task_id"]: item["answer_text"] for item in untouched}

    task = _first_editable_task(before)
    client.post(
        f"/workspaces/{job_id}/edits",
        json={"edits": [{"task_id": task["task_id"], "text": "Only one answer changed."}]},
    )

    after = client.get(f"/workspaces/{job_id}/review").json()
    for item in after["answered"]:
        if item["task_id"] in original_map and item["task_id"] != task["task_id"]:
            assert item["answer_text"] == original_map[item["task_id"]]


def test_edited_task_is_tracked(client: TestClient) -> None:
    job_id = _upload(client, "placement_integration.docx")
    review = client.get(f"/workspaces/{job_id}/review").json()
    task = _first_editable_task(review)
    client.post(
        f"/workspaces/{job_id}/edits",
        json={"edits": [{"task_id": task["task_id"], "text": "Tracked edit."}]},
    )
    detail = client.get(f"/workspaces/{job_id}").json()
    assert task["task_id"] in detail["edited_task_ids"]


def test_workspace_updated_at_changes_after_edit(client: TestClient) -> None:
    job_id = _upload(client, "placement_integration.docx")
    before = client.get(f"/workspaces/{job_id}").json()
    review = client.get(f"/workspaces/{job_id}/review").json()
    task = _first_editable_task(review)
    time.sleep(0.01)
    client.post(
        f"/workspaces/{job_id}/edits",
        json={"edits": [{"task_id": task["task_id"], "text": "Timestamp bump."}]},
    )
    after = client.get(f"/workspaces/{job_id}").json()
    assert after["updated_at"] >= before["updated_at"]


def test_rename_changes_display_name_only(client: TestClient, temp_settings: Settings) -> None:
    job_id = _upload(client, "blank_run.docx")
    fixture_name = client.get(f"/workspaces/{job_id}").json()["document_name"]
    original_path = temp_settings.storage_dir / job_id / "original" / "input.docx"
    before_bytes = original_path.read_bytes()

    renamed = client.post(
        f"/workspaces/{job_id}/rename",
        json={"display_name": "UHV-II Worksheet"},
    )
    assert renamed.status_code == 200
    payload = renamed.json()
    assert payload["display_name"] == "UHV-II Worksheet"
    assert payload["document_name"] == fixture_name
    assert original_path.read_bytes() == before_bytes


def test_delete_removes_workspace_artifacts(client: TestClient, temp_settings: Settings) -> None:
    job_id = _upload(client)
    root = temp_settings.storage_dir / job_id
    assert root.exists()
    deleted = client.delete(f"/workspaces/{job_id}")
    assert deleted.status_code == 200
    assert not root.exists()


def test_delete_does_not_affect_other_workspace(client: TestClient, temp_settings: Settings) -> None:
    keep = _upload(client, "blank_run.docx")
    remove = _upload(client, "placement_integration.docx")
    response = client.delete(f"/workspaces/{remove}")
    assert response.status_code == 200
    assert (temp_settings.storage_dir / keep).exists()
    assert not (temp_settings.storage_dir / remove).exists()


def test_missing_workspace_returns_404(client: TestClient) -> None:
    response = client.get("/workspaces/does-not-exist")
    assert response.status_code == 404


def test_failed_workspace_is_safe(client: TestClient, service: DocNAService, monkeypatch) -> None:
    def fail_process(job_id: str):
        paths = service.store.get_paths(job_id)
        service.store.update_status(job_id, "failed", errors=[])
        service.store.sync_workspace_from_job(job_id)

    monkeypatch.setattr(service, "process_job", fail_process)
    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("blank_run.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    detail = client.get(f"/workspaces/{job_id}").json()
    assert detail["status"] == "failed"
    assert contains_locator_payload(detail) is False


def test_existing_review_flow_still_works(client: TestClient) -> None:
    job_id = _upload(client, "placement_integration.docx")
    review = client.get(f"/jobs/{job_id}/review").json()
    assert review["status"] == "completed"
    task = _first_editable_task(review)
    applied = client.post(
        f"/jobs/{job_id}/edits",
        json={"edits": [{"task_id": task["task_id"], "text": "Legacy edit path."}]},
    )
    assert applied.status_code == 200


def test_existing_export_flow_still_works(client: TestClient) -> None:
    job_id = _upload(client, "placement_integration.docx")
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)
    client.post(
        f"/jobs/{job_id}/edits",
        json={"edits": [{"task_id": task["task_id"], "text": "Export me."}]},
    )
    download = client.get(f"/jobs/{job_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_workspace_list_excludes_internal_upload_dir(client: TestClient, temp_settings: Settings) -> None:
    _upload(client)
    (temp_settings.storage_dir / "_uploads").mkdir(parents=True, exist_ok=True)
    listed = client.get("/workspaces").json()["workspaces"]
    assert all(not item["workspace_id"].startswith("_") for item in listed)


def test_post_jobs_creates_workspace_immediately(
    client: TestClient, service: DocNAService, monkeypatch: pytest.MonkeyPatch
) -> None:
    def stall_process(job_id: str) -> None:
        service.store.update_status(job_id, "processing")
        service.store.sync_workspace_from_job(job_id)

    monkeypatch.setattr(service, "process_job", stall_process)
    fixture = ensure_placement_fixture("blank_run.docx")

    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("1011.docx", handle, "application/octet-stream")},
        )
    assert created.status_code == 200
    payload = created.json()
    job_id = payload["job_id"]
    assert payload["workspace_id"] == job_id

    workspace_path = service.store.get_paths(job_id).workspace
    assert workspace_path.exists()
    detail = client.get(f"/workspaces/{job_id}").json()
    assert detail["status"] == "processing"
    assert detail["document_name"] == "1011.docx"


def test_processing_workspace_appears_in_get_workspaces(
    client: TestClient, service: DocNAService, monkeypatch: pytest.MonkeyPatch
) -> None:
    def stall_process(job_id: str) -> None:
        service.store.update_status(job_id, "processing")
        service.store.sync_workspace_from_job(job_id)

    monkeypatch.setattr(service, "process_job", stall_process)
    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("processing_now.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]

    response = client.get("/workspaces")
    assert response.status_code == 200
    workspaces = response.json()["workspaces"]
    match = next(item for item in workspaces if item["workspace_id"] == job_id)
    assert match["status"] == "processing"
    assert match["document_name"] == "processing_now.docx"


def test_list_workspaces_tolerates_legacy_review_json(
    client: TestClient, service: DocNAService
) -> None:
    job_id = _upload(client, "placement_integration.docx")
    paths = service.store.get_paths(job_id)
    paths.review.write_text(
        json.dumps({"answered": [], "skipped": [], "flagged": []}),
        encoding="utf-8",
    )

    response = client.get("/workspaces")
    assert response.status_code == 200
    ids = {item["workspace_id"] for item in response.json()["workspaces"]}
    assert job_id in ids

    detail = client.get(f"/workspaces/{job_id}").json()
    assert detail["workspace_id"] == job_id
    assert contains_locator_payload(detail) is False


def test_reopen_processing_workspace_reuses_existing_job(
    client: TestClient, service: DocNAService, monkeypatch: pytest.MonkeyPatch
) -> None:
    process_calls: list[str] = []

    def stall_process(job_id: str) -> None:
        process_calls.append(job_id)
        service.store.update_status(job_id, "processing")
        service.store.sync_workspace_from_job(job_id)

    monkeypatch.setattr(service, "process_job", stall_process)
    fixture = ensure_placement_fixture("blank_run.docx")
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": ("resume_me.docx", handle, "application/octet-stream")},
        )
    job_id = created.json()["job_id"]
    assert process_calls == [job_id]

    detail = client.get(f"/workspaces/{job_id}").json()
    assert detail["status"] == "processing"
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "processing"
    assert status["job_id"] == job_id
    assert len(process_calls) == 1


def test_deleted_workspace_cannot_be_reopened(client: TestClient) -> None:
    job_id = _upload(client)
    deleted = client.delete(f"/workspaces/{job_id}")
    assert deleted.status_code == 200
    assert client.get(f"/workspaces/{job_id}").status_code == 404


def test_rename_updates_workspace_list_metadata(client: TestClient) -> None:
    job_id = _upload(client, "blank_run.docx")
    renamed = client.post(
        f"/workspaces/{job_id}/rename",
        json={"display_name": "Renamed Worksheet"},
    )
    assert renamed.status_code == 200
    listed = client.get("/workspaces").json()["workspaces"]
    match = next(item for item in listed if item["workspace_id"] == job_id)
    assert match["display_name"] == "Renamed Worksheet"
    assert match["document_name"] == "blank_run.docx"


def test_app_upload_is_user_library_workspace(client: TestClient, temp_settings: Settings) -> None:
    job_id = _upload(client, "blank_run.docx")
    workspace = json.loads((temp_settings.storage_dir / job_id / "workspace.json").read_text(encoding="utf-8"))
    assert workspace["library_kind"] == "user"


def test_internal_job_hidden_from_documents_library(client: TestClient, service: DocNAService) -> None:
    paths = service.store.create_job(b"placeholder", "internal_fixture.docx")
    service.store.sync_workspace_from_job(paths.job_id)

    listed = client.get("/workspaces").json()["workspaces"]
    ids = {item["workspace_id"] for item in listed}
    assert paths.job_id not in ids

    detail = client.get(f"/workspaces/{paths.job_id}")
    assert detail.status_code == 200


def test_user_and_internal_jobs_coexist_in_storage(client: TestClient, service: DocNAService) -> None:
    user_id = _upload(client, "placement_integration.docx")
    internal_paths = service.store.create_job(b"x", "stress_test.docx")
    service.store.sync_workspace_from_job(internal_paths.job_id)

    listed = client.get("/workspaces").json()["workspaces"]
    ids = {item["workspace_id"] for item in listed}
    assert user_id in ids
    assert internal_paths.job_id not in ids
    assert len(ids) == 1


