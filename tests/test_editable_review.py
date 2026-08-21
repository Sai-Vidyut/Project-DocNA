"""Phase 11 editable human review tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app, get_service, get_settings
from docna.adapters.docx import DocxAdapter
from docna.config import Settings
from docna.edit_apply import apply_edited_answers
from docna.review_edits import AnswerEdit, ApplyEditsRequest, ReviewEditError
from docna.serializers import contains_locator_payload
from docna.service import DocNAService
from docna.storage.jobs import JobStore
from tests.conftest import frontend_source_text
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


def _create_completed_job(client: TestClient, fixture_name: str = "blank_run.docx") -> str:
    fixture = ensure_placement_fixture(fixture_name)
    with fixture.open("rb") as handle:
        created = client.post(
            "/jobs",
            files={"file": (fixture_name, handle, "application/octet-stream")},
        )
    assert created.status_code == 200
    job_id = created.json()["job_id"]
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"
    return job_id


def _first_editable_task(review: dict) -> dict:
    for item in review["answered"]:
        if item.get("editable"):
            return item
    raise AssertionError("No editable task found in review")


def _apply_edits(client: TestClient, job_id: str, edits: list[dict]) -> dict:
    response = client.post(f"/jobs/{job_id}/edits", json={"edits": edits})
    assert response.status_code == 200, response.text
    return response.json()


def test_editing_one_answer_updates_docx_and_review(
    client: TestClient, service: DocNAService
) -> None:
    job_id = _create_completed_job(client, "placement_integration.docx")
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)
    original_text = task["answer_text"]
    edited_text = "User edited answer for integration test."

    _apply_edits(client, job_id, [{"task_id": task["task_id"], "text": edited_text}])

    updated_review = client.get(f"/jobs/{job_id}/review").json()
    updated = next(item for item in updated_review["answered"] if item["task_id"] == task["task_id"])
    assert updated["answer_text"] == edited_text
    assert updated["edited"] is True
    assert updated["answer_source"] == "user"
    assert updated_review["download_ready"] is True

    download = client.get(f"/jobs/{job_id}/download")
    assert download.status_code == 200
    reparsed = DocxAdapter().parse(service.store.get_paths(job_id).edited_output_file)
    assert any(edited_text in block.text for block in reparsed.blocks)
    assert not any(
        original_text in block.text and edited_text not in block.text
        for block in reparsed.blocks
        if original_text
    )


def test_editing_multiple_answers(client: TestClient, service: DocNAService) -> None:
    job_id = _create_completed_job(client, "placement_integration.docx")
    review = client.get(f"/jobs/{job_id}/review").json()
    editable = [item for item in review["answered"] if item.get("editable")][:2]
    assert len(editable) >= 1
    edits = [
        {"task_id": item["task_id"], "text": f"Edited answer {index + 1}"}
        for index, item in enumerate(editable)
    ]
    _apply_edits(client, job_id, edits)
    updated = client.get(f"/jobs/{job_id}/review").json()
    for edit in edits:
        item = next(row for row in updated["answered"] if row["task_id"] == edit["task_id"])
        assert item["answer_text"] == edit["text"]
        assert item["edited"] is True


def test_leaving_answers_unchanged_still_prepares_download(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    payload = _apply_edits(client, job_id, [])
    assert payload["message"] == "Your document is ready."
    review = client.get(f"/jobs/{job_id}/review").json()
    assert review["download_ready"] is True
    assert client.get(f"/jobs/{job_id}/download").status_code == 200


def test_edited_answer_appears_in_final_docx(client: TestClient, service: DocNAService) -> None:
    job_id = _create_completed_job(client)
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)
    edited_text = "Final edited answer text."
    _apply_edits(client, job_id, [{"task_id": task["task_id"], "text": edited_text}])
    paths = service.store.get_paths(job_id)
    reparsed = DocxAdapter().parse(paths.edited_output_file)
    assert any(edited_text in block.text for block in reparsed.blocks)


def test_original_docx_remains_byte_identical(
    client: TestClient, service: DocNAService
) -> None:
    fixture = ensure_placement_fixture("blank_run.docx")
    before = sha256_file(fixture)
    job_id = _create_completed_job(client, fixture.name)
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)
    _apply_edits(client, job_id, [{"task_id": task["task_id"], "text": "Immutable original check."}])
    paths = service.store.get_paths(job_id)
    assert sha256_file(paths.original) == before


def test_failed_edit_application_preserves_previous_output(
    client: TestClient, service: DocNAService, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_id = _create_completed_job(client)
    paths = service.store.get_paths(job_id)
    ai_hash = sha256_file(paths.output_file)
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)

    def boom(*_args, **_kwargs):
        raise RuntimeError("apply failed")

    monkeypatch.setattr("docna.edit_apply._apply_placements", boom)
    response = client.post(
        f"/jobs/{job_id}/edits",
        json={"edits": [{"task_id": task["task_id"], "text": "Should not be written."}]},
    )
    assert response.status_code == 400
    assert sha256_file(paths.output_file) == ai_hash
    assert not paths.edited_output_file.exists()


def test_invalid_task_id_rejected(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    response = client.post(
        f"/jobs/{job_id}/edits",
        json={"edits": [{"task_id": "task_does_not_exist", "text": "Nope."}]},
    )
    assert response.status_code == 400


def test_task_id_from_other_job_rejected(client: TestClient, service: DocNAService) -> None:
    job_a = _create_completed_job(client, "blank_run.docx")
    job_b = _create_completed_job(client, "placement_integration.docx")
    review_a = client.get(f"/jobs/{job_a}/review").json()
    task_a = _first_editable_task(review_a)
    review_b = client.get(f"/jobs/{job_b}/review").json()
    editable_b = {item["task_id"] for item in review_b["answered"] if item.get("editable")}
    foreign_id = task_a["task_id"]
    if foreign_id in editable_b:
        foreign_id = "task_foreign_only"
    response = client.post(
        f"/jobs/{job_b}/edits",
        json={"edits": [{"task_id": foreign_id, "text": "Cross-job attempt."}]},
    )
    assert response.status_code == 400


def test_locator_payload_in_request_is_rejected(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)
    response = client.post(
        f"/jobs/{job_id}/edits",
        json={
            "edits": [
                {
                    "task_id": task["task_id"],
                    "text": "Edited",
                    "target": {"adapter": "docx", "payload": {"body_index": 1}},
                }
            ]
        },
    )
    assert response.status_code == 422


def test_placement_strategy_in_request_is_rejected(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)
    response = client.post(
        f"/jobs/{job_id}/edits",
        json={
            "edits": [
                {
                    "task_id": task["task_id"],
                    "text": "Edited",
                    "strategy": "insert_below",
                }
            ]
        },
    )
    assert response.status_code == 422


def test_skipped_task_cannot_be_edited(client: TestClient, service: DocNAService) -> None:
    job_id = _create_completed_job(client, "placement_integration.docx")
    paths = service.store.get_paths(job_id)
    ops = service.store.load_placement_ops(paths)
    skipped_op = next(op for op in ops if op.strategy == "skip")
    response = client.post(
        f"/jobs/{job_id}/edits",
        json={"edits": [{"task_id": skipped_op.task_id, "text": "Should fail."}]},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("fixture_name", "edited_text", "strategy"),
    [
        ("blank_run.docx", "Edited insert-below answer", "insert_below"),
        ("nested_questions.docx", "Edited insert-below answer", "insert_below"),
        ("placement_integration.docx", "First paragraph.\n\nSecond paragraph.", "fill_existing"),
        ("placement_integration.docx", "Edited table cell answer", "fill_cell"),
    ],
)
def test_edit_strategies_via_existing_placement_architecture(
    client: TestClient,
    service: DocNAService,
    fixture_name: str,
    edited_text: str,
    strategy: str,
) -> None:
    job_id = _create_completed_job(client, fixture_name)
    paths = service.store.get_paths(job_id)
    ops = service.store.load_placement_ops(paths)
    target_op = next(op for op in ops if op.strategy == strategy)
    _apply_edits(client, job_id, [{"task_id": target_op.task_id, "text": edited_text}])
    reparsed = DocxAdapter().parse(paths.edited_output_file)
    block_text = "\n".join(block.text for block in reparsed.blocks)
    assert edited_text.split("\n\n")[0] in block_text or edited_text in block_text


def test_download_and_review_still_work_after_edits(client: TestClient) -> None:
    job_id = _create_completed_job(client)
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)
    _apply_edits(client, job_id, [{"task_id": task["task_id"], "text": "Download check."}])
    review_after = client.get(f"/jobs/{job_id}/review").json()
    assert not contains_locator_payload(review_after)
    download = client.get(f"/jobs/{job_id}/download")
    assert download.status_code == 200
    assert download.content.startswith(b"PK")


@pytest.fixture
def job_store(temp_settings: Settings) -> JobStore:
    return JobStore(temp_settings.storage_dir)


def test_pipeline_persists_internal_placement_artifacts(
    job_store: JobStore, tmp_path: Path
) -> None:
    from docna.pipeline import run_job

    fixture = ensure_placement_fixture("blank_run.docx")
    paths = job_store.create_job(fixture.read_bytes(), fixture.name)
    settings = Settings.from_env(storage_dir=tmp_path / "jobs")
    run_job(job_store, paths, pipeline_mock_provider(), settings=settings)
    assert paths.placement_ops_file.exists()
    assert paths.tasks_file.exists()
    assert paths.answers_file.exists()
    payload = json.loads(paths.placement_ops_file.read_text(encoding="utf-8"))
    assert payload
    assert "payload" in json.dumps(payload)


def test_frontend_has_apply_and_editable_markup() -> None:
    source = frontend_source_text()
    assert "saveWorkspaceEdits" in source
    assert "Changes save automatically" in source
    assert "card-answer-input" in source
    assert "document-preview" in source
    assert "review-document-scroll" in source
    assert "review-questions-scroll" in source


def test_ai_completed_output_preserved_when_edited_output_created(
    client: TestClient, service: DocNAService
) -> None:
    job_id = _create_completed_job(client)
    paths = service.store.get_paths(job_id)
    ai_hash = hashlib.sha256(paths.output_file.read_bytes()).hexdigest()
    review = client.get(f"/jobs/{job_id}/review").json()
    task = _first_editable_task(review)
    _apply_edits(client, job_id, [{"task_id": task["task_id"], "text": "Separate edited file."}])
    assert paths.edited_output_file.exists()
    assert hashlib.sha256(paths.output_file.read_bytes()).hexdigest() == ai_hash


def test_apply_edits_directly_raises_safe_error_for_missing_artifacts(
    job_store: JobStore, tmp_path: Path
) -> None:
    fixture = ensure_placement_fixture("blank_run.docx")
    paths = job_store.create_job(fixture.read_bytes(), fixture.name)
    job_store.update_status(paths.job_id, "completed", output_ready=True)
    with pytest.raises(ReviewEditError):
        apply_edited_answers(job_store, paths, edits=[])
