"""Scoped AI assistance for individual review questions."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from docna.adapters.docx import DocxAdapter
from docna.ai.port import AIProvider, ChatMessage
from docna.ai.prompts.task_assistance import (
    TASK_ASSISTANCE_SYSTEM_PROMPT,
    build_task_assist_user_prompt,
)
from docna.answer.context import build_context_pack
from docna.answer.context import render_context_for_prompt
from docna.detect.content_policy import classify_answer_mode
from docna.ir import DocumentIR, Task
from docna.storage.jobs import JobStore, JobPaths


class AssistMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1)


class TaskAssistRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    history: list[AssistMessage] = Field(default_factory=list, max_length=20)


class TaskAssistResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str
    example_response: str | None = None
    is_example: bool = False


class TaskAssistError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def assist_with_task(
    *,
    store: JobStore,
    paths: JobPaths,
    provider: AIProvider,
    task_id: str,
    request: TaskAssistRequest,
) -> TaskAssistResponse:
    if not store.has_pipeline_artifacts(paths):
        raise TaskAssistError("Task assistance is not available for this job.")

    tasks = store.load_tasks(paths)
    task = next((item for item in tasks if item.task_id == task_id), None)
    if task is None:
        raise TaskAssistError("Question not found.")

    adapter = DocxAdapter()
    ir = adapter.parse(paths.original)
    answer_mode = classify_answer_mode(
        task.prompt_text,
        has_document_content=bool(ir.blocks),
    )
    pack = build_context_pack(ir, task, all_tasks=tasks)
    context_text = render_context_for_prompt(pack)

    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=TASK_ASSISTANCE_SYSTEM_PROMPT),
    ]
    for item in request.history[-8:]:
        messages.append(
            ChatMessage(role=item.role, content=item.content)  # type: ignore[arg-type]
        )
    messages.append(
        ChatMessage(
            role="user",
            content=build_task_assist_user_prompt(
                task_id=task.task_id,
                question=task.prompt_text,
                answer_mode=answer_mode,
                context_text=context_text,
                user_message=request.message,
            ),
        )
    )

    response = provider.complete(messages, TaskAssistResponse)
    if not isinstance(response, TaskAssistResponse):
        raise TaskAssistError("Unexpected assistance response.")
    return response
