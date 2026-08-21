"""Shared helpers for pipeline and API tests."""

from __future__ import annotations

import re
from collections.abc import Sequence

from docna.ai.mock import MockAIProvider
from docna.ai.port import ChatMessage
from docna.answer.models import AnswerGenerationResponse
from docna.detect.models import SemanticClassificationItem, SemanticClassificationResponse
from tests.detect_helpers import BLOCK_LINE_RE, classify_text


def pipeline_mock_provider() -> MockAIProvider:
    """Mock provider for semantic detection and answer generation."""

    def responder(messages: Sequence[ChatMessage], schema: type):
        if "classifications" in getattr(schema, "model_fields", {}):
            return _semantic_response(messages, schema)
        if "answer" in getattr(schema, "model_fields", {}):
            return _answer_response(messages, schema)
        if "message" in getattr(schema, "model_fields", {}):
            return schema.model_validate(
                {
                    "message": "This question asks for your reflection.",
                    "example_response": "Example response for testing.",
                    "is_example": True,
                }
            )
        return schema.model_validate({})

    return MockAIProvider(responder=responder)


def _semantic_response(messages: Sequence[ChatMessage], schema: type):
    preview = messages[-1].content
    items: list[SemanticClassificationItem] = []
    for line in preview.splitlines():
        match = BLOCK_LINE_RE.match(line)
        if not match:
            continue
        header, text = match.groups()
        block_id = header.split()[0]
        if block_id.startswith("space_") or block_id.startswith("tbl_"):
            continue
        if block_id.startswith("blk_"):
            kind, confidence = classify_text(text)
            items.append(
                SemanticClassificationItem(
                    block_id=block_id,
                    kind=kind,  # type: ignore[arg-type]
                    confidence=confidence,
                    reason=f"rule:{kind}",
                )
            )
    return SemanticClassificationResponse(classifications=items)


def _answer_response(messages: Sequence[ChatMessage], schema: type):
    content = messages[-1].content
    task_match = re.search(r"Required task_id:\s*(\S+)", content)
    task_id = task_match.group(1) if task_match else "task_0001"
    task_text_match = re.search(r"Task \([^)]+\):\s*(.+)", content)
    task_text = task_text_match.group(1).strip() if task_text_match else "task"
    return AnswerGenerationResponse.model_validate(
        {
            "answer": {
                "task_id": task_id,
                "text": f"Answer for {task_text[:40]}",
                "confidence": 0.95,
            }
        }
    )
