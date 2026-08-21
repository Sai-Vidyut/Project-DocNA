"""Fresh-install import smoke tests."""

from __future__ import annotations

import importlib

MODULES = (
    "docna",
    "docna.ir",
    "docna.pipeline",
    "docna.pipeline_models",
    "docna.config",
    "docna.ingest",
    "docna.review",
    "docna.serializers",
    "docna.service",
    "docna.detect",
    "docna.detect.structural",
    "docna.detect.content_policy",
    "docna.detect.semantic",
    "docna.detect.merge",
    "docna.detect.run",
    "docna.detect.config",
    "docna.detect.models",
    "docna.answer",
    "docna.answer.context",
    "docna.answer.generate",
    "docna.answer.config",
    "docna.answer.generation_config",
    "docna.answer.models",
    "docna.place",
    "docna.place.planner",
    "docna.place.policy",
    "docna.ai",
    "docna.ai.port",
    "docna.ai.mock",
    "docna.ai.metrics",
    "docna.ai.instrumented",
    "docna.ai.factory",
    "docna.ai.fallback",
    "docna.ai.fallback_policy",
    "docna.ai.structured",
    "docna.ai.providers.spec",
    "docna.ai.providers.builder",
    "docna.ai.providers.gemini",
    "docna.ai.providers.openai_compatible",
    "docna.ai.openai_provider",
    "docna.ai.prompts.semantic_classification",
    "docna.ai.prompts.answer_generation",
    "docna.adapters",
    "docna.adapters.base",
    "docna.adapters.registry",
    "docna.adapters.docx",
    "docna.adapters.docx.parse",
    "docna.adapters.docx.apply",
    "docna.adapters.docx.locators",
    "docna.adapters.pdf",
    "docna.adapters.txt",
    "docna.adapters.md",
    "docna.adapters.pptx",
    "docna.storage",
    "docna.storage.jobs",
)


def test_project_imports_cleanly() -> None:
    for name in MODULES:
        module = importlib.import_module(name)
        assert module is not None


def test_public_package_exports() -> None:
    import docna

    for symbol in (
        "Locator",
        "Block",
        "TableView",
        "AnswerSpace",
        "DocumentIR",
        "Task",
        "Answer",
        "PlacementOp",
    ):
        assert hasattr(docna, symbol)
