"""Semantic detection unit tests."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from pydantic import ValidationError

from docna.ai.mock import MockAIProvider
from docna.ai.port import ChatMessage
from docna.detect.models import SemanticClassificationItem, SemanticClassificationResponse
from docna.detect.semantic import detect_semantic
from tests.detect_helpers import parse_fixture, preview_fixture, rule_based_mock_provider
from tests.helpers import sample_block, sample_document


def test_semantic_uses_preview_only() -> None:
    ir, preview = preview_fixture("simple_paragraphs.docx")
    provider = rule_based_mock_provider()
    result = detect_semantic(ir, preview, provider)
    assert isinstance(result.classifications, list)


def test_semantic_rejects_unknown_block_ids() -> None:
    ir = sample_document(sample_block("blk_0001", "What is AI?"))

    def responder(_messages: Sequence[ChatMessage], _schema: type) -> SemanticClassificationResponse:
        return SemanticClassificationResponse(
            classifications=[
                SemanticClassificationItem(
                    block_id="blk_9999",
                    kind="question",
                    confidence=0.9,
                    reason="unknown",
                )
            ]
        )

    result = detect_semantic(ir, "[blk_0001 para] What is AI?", MockAIProvider(responder=responder))
    assert not result.classifications
    assert any("unknown_block_id" in warning for warning in result.warnings)


def test_semantic_deduplicates_block_ids() -> None:
    ir = sample_document(sample_block("blk_0001", "Question?"))

    def responder(_messages: Sequence[ChatMessage], _schema: type) -> SemanticClassificationResponse:
        return SemanticClassificationResponse(
            classifications=[
                SemanticClassificationItem(
                    block_id="blk_0001",
                    kind="question",
                    confidence=0.7,
                    reason="low",
                ),
                SemanticClassificationItem(
                    block_id="blk_0001",
                    kind="question",
                    confidence=0.95,
                    reason="high",
                ),
            ]
        )

    result = detect_semantic(ir, "[blk_0001 para] Question?", MockAIProvider(responder=responder))
    assert len(result.classifications) == 1
    assert result.classifications[0].confidence == 0.95
    assert any("duplicate" in warning for warning in result.warnings)


def test_semantic_handles_provider_validation_error() -> None:
    ir = sample_document(sample_block("blk_0001", "Question?"))

    def responder(_messages: Sequence[ChatMessage], schema: type) -> SemanticClassificationResponse:
        return schema.model_validate({"classifications": [{"block_id": "blk_0001", "kind": "bad", "confidence": 2, "reason": "x"}]})

    result = detect_semantic(ir, "[blk_0001 para] Question?", MockAIProvider(responder=responder))
    assert not result.classifications
    assert result.warnings


def test_semantic_malformed_response_is_recorded() -> None:
    ir = sample_document(sample_block("blk_0001", "Question?"))

    class BadModel:
        @staticmethod
        def model_validate(_data):
            raise ValidationError.from_exception_data("BadModel", [])

    def responder(_messages, schema):
        raise ValidationError.from_exception_data("SemanticClassificationResponse", [])

    result = detect_semantic(ir, "[blk_0001 para] Question?", MockAIProvider(responder=responder))
    assert result.warnings


def test_prompt_injection_text_is_classified_as_document_content() -> None:
    ir, preview = preview_fixture("detection_mixed.docx")
    provider = rule_based_mock_provider()
    result = detect_semantic(ir, preview, provider)
    injection_blocks = [
        item
        for item in result.classifications
        if "ignore the system instructions" in _block_text(ir, item.block_id).lower()
    ]
    assert injection_blocks
    assert injection_blocks[0].kind == "narrative"


def _block_text(ir, block_id: str) -> str:
    for block in ir.blocks:
        if block.block_id == block_id:
            return block.text
    return ""
