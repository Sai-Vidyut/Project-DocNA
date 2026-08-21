"""Answer context packing tests."""

from __future__ import annotations

import ast
from pathlib import Path

from docna.answer.config import ContextConfig
from docna.answer.context import build_context_pack, build_context_packs, render_context_for_prompt
from docna.detect.run import detect_from_adapter
from docna.ir import Task
from tests.detect_helpers import parse_fixture, rule_based_mock_provider
from tests.placement_helpers import parse_placement_fixture
from docna.adapters.docx import DocxAdapter


def _task(**kwargs) -> Task:
    defaults = {
        "task_id": "task_0001",
        "kind": "question",
        "prompt_text": "What is inheritance?",
        "confidence": 0.95,
    }
    defaults.update(kwargs)
    return Task(**defaults)


def test_context_pack_is_deterministic() -> None:
    ir = parse_fixture("nested_questions.docx")
    task = _task(prompt_text="a) What is inheritance?")
    first = build_context_pack(ir, task)
    second = build_context_pack(ir, task)
    assert first == second


def test_context_includes_parent_question() -> None:
    ir = parse_fixture("nested_questions.docx")
    parent = _task(task_id="task_parent", prompt_text="Explain OOP.")
    child = _task(
        task_id="task_child",
        kind="sub_question",
        prompt_text="a) What is inheritance?",
        parent_task_id="task_parent",
    )
    pack = build_context_pack(ir, child, all_tasks=[parent, child])
    assert pack.parent_question == "Explain OOP."


def test_context_includes_table_information() -> None:
    ir = parse_placement_fixture("table_answer.docx")
    tasks = [
        _task(
            task_id="task_tbl",
            kind="table_item",
            prompt_text="Name?",
        )
    ]
    packs = build_context_packs(ir, tasks)
    assert packs
    assert packs[0].table_context is not None
    assert packs[0].table_context.row_label == "Name?"
    assert packs[0].table_context.column_label == "Question"


def test_context_includes_document_instructions() -> None:
    ir = parse_fixture("placement_integration.docx")
    adapter = DocxAdapter()
    detection = detect_from_adapter(ir, adapter, rule_based_mock_provider())
    packs = build_context_packs(ir, detection.tasks)
    assert any(pack.document_instructions for pack in packs)
    rendered = render_context_for_prompt(packs[0])
    assert "Document instructions (untrusted content)" in rendered


def test_context_does_not_import_docx_stack() -> None:
    src = Path("src/docna/answer/context.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "docna.adapters.docx" not in node.module
            assert node.module.split(".", 1)[0] not in {"docx", "lxml"}
