"""Integration test: DOCX → IR → Tasks → Context → Answers."""

from __future__ import annotations

from docna.adapters.docx import DocxAdapter
from docna.answer.context import build_context_packs
from docna.answer.generate import generate_answers
from docna.answer.generation_config import GenerationConfig
from docna.answer.models import AnswerGenerationResponse
from docna.ai.mock import MockAIProvider
from docna.detect.run import detect_from_adapter
from tests.detect_helpers import parse_fixture, rule_based_mock_provider


def test_docx_to_answers_without_placement() -> None:
    ir = parse_fixture("detection_mixed.docx")
    adapter = DocxAdapter()
    detection = detect_from_adapter(ir, adapter, rule_based_mock_provider())
    packs = build_context_packs(ir, detection.tasks)
    assert packs

    def responder(messages, schema):
        for pack in packs:
            if pack.task_id in messages[-1].content:
                return AnswerGenerationResponse.model_validate(
                    {
                        "answer": {
                            "task_id": pack.task_id,
                            "text": f"Answer for {pack.task_text[:20]}",
                            "confidence": 0.92,
                        }
                    }
                )
        return AnswerGenerationResponse.model_validate(
            {
                "answer": {
                    "task_id": packs[0].task_id,
                    "text": "Fallback answer",
                    "confidence": 0.8,
                }
            }
        )

    provider = MockAIProvider(responder=responder)
    result = generate_answers(packs, provider, config=GenerationConfig(batch_size=1))
    assert result.answers
    assert len(result.answers) <= len(packs)
    assert all(answer.text for answer in result.answers)
