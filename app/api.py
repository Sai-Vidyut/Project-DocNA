"""FastAPI application for DocNA job upload and retrieval."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from docna.config import Settings
from docna.ingest import ValidationError
from docna.serializers import contains_locator_payload
from docna.review_edits import ApplyEditsRequest
from docna.service import DocNAService, JobNotReadyError, ReviewEditValidationError
from docna.storage.jobs import JobNotFoundError
from docna.task_assist import TaskAssistRequest
from docna.workspace import WorkspaceEditsRequest, WorkspaceRenameRequest

logger = logging.getLogger(__name__)

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
WEB_SRC = Path(__file__).resolve().parent.parent / "web" / "src"
FRONTEND_DIR = WEB_DIST

app = FastAPI(title="DocNA", version="0.1.0")


def get_settings() -> Settings:
    return Settings.from_env()


def get_service(settings: Settings = Depends(get_settings)) -> DocNAService:
    return DocNAService(settings)


@app.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        job_id = service.create_job_from_upload(data, file.filename)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to accept upload")
        raise HTTPException(status_code=500, detail="Failed to accept upload") from exc

    background_tasks.add_task(service.process_job, job_id)
    return JSONResponse({"job_id": job_id, "workspace_id": job_id, "status": "queued"})


@app.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.get_job_status(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.get("/jobs/{job_id}/download")
async def download_job(
    job_id: str,
    service: DocNAService = Depends(get_service),
) -> FileResponse:
    try:
        output_path = service.get_completed_output_path(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except JobNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return FileResponse(
        path=output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="completed.docx",
    )


@app.get("/jobs/{job_id}/review")
async def get_review(
    job_id: str,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.get_review(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Review report is not available") from exc

    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.post("/jobs/{job_id}/edits")
async def apply_review_edits(
    job_id: str,
    request: ApplyEditsRequest,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.apply_review_edits(job_id, request)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except ReviewEditValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to apply review edits for job %s", job_id)
        raise HTTPException(
            status_code=500,
            detail="DocNA could not apply your edits. Please try again.",
        ) from exc

    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.get("/jobs/{job_id}/preview")
async def get_document_preview(
    job_id: str,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.get_document_preview(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except JobNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.post("/jobs/{job_id}/tasks/{task_id}/assist")
async def assist_task(
    job_id: str,
    task_id: str,
    request: TaskAssistRequest,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.assist_task(job_id, task_id, request)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except JobNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ReviewEditValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed task assistance for job %s task %s", job_id, task_id)
        raise HTTPException(
            status_code=500,
            detail="DocNA could not assist with this question. Please try again.",
        ) from exc

    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.get("/workspaces")
async def list_workspaces(
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    payload = {"workspaces": [item.model_dump(mode="json") for item in service.list_workspaces()]}
    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.get("/workspaces/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.get_workspace(workspace_id).model_dump(mode="json")
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found") from exc
    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.post("/workspaces/{workspace_id}/rename")
async def rename_workspace(
    workspace_id: str,
    request: WorkspaceRenameRequest,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.rename_workspace(workspace_id, request).model_dump(mode="json")
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found") from exc
    except ReviewEditValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        service.delete_workspace(workspace_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found") from exc
    except OSError as exc:
        logger.exception("Failed to delete workspace %s", workspace_id)
        raise HTTPException(status_code=500, detail="Could not delete this document.") from exc
    return JSONResponse({"status": "deleted"})


@app.get("/workspaces/{workspace_id}/review")
async def get_workspace_review(
    workspace_id: str,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.get_workspace_review(workspace_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found") from exc
    except JobNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Review report is not available") from exc
    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


@app.post("/workspaces/{workspace_id}/edits")
async def apply_workspace_edits(
    workspace_id: str,
    request: WorkspaceEditsRequest,
    service: DocNAService = Depends(get_service),
) -> JSONResponse:
    try:
        payload = service.apply_workspace_edits(workspace_id, request)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workspace not found") from exc
    except ReviewEditValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to save workspace edits for %s", workspace_id)
        raise HTTPException(
            status_code=500,
            detail="DocNA could not save your changes. Please try again.",
        ) from exc
    if contains_locator_payload(payload):
        raise HTTPException(status_code=500, detail="Internal serialization error")
    return JSONResponse(payload)


if WEB_DIST.is_dir():
    assets_dir = WEB_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    async def serve_frontend() -> FileResponse:
        return FileResponse(WEB_DIST / "index.html")
