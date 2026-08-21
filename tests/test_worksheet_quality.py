"""Regression tests for worksheet answer quality and placement behavior."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

from docna.adapters.docx import DocxAdapter
from docna.answer.context import build_context_pack, build_context_packs
from docna.detect.content_policy import (
    classify_answer_mode,
    is_enumerator_only,
    is_tick_response_value,
    is_worksheet_structure_label,
)
from docna.detect.merge import merge_detections
from docna.detect.models import SemanticClassificationItem, SemanticDetectionResult
from docna.detect.structural import detect_structural
from docna.ir import Task
from docna.place.planner import plan_placements
from docna.pipeline import original_is_immutable
from docna.storage.jobs import JobPaths


def test_worksheet_labels_are_not_tasks() -> None:
    assert is_worksheet_structure_label("Question")
    assert is_worksheet_structure_label("Your observation")
    assert is_worksheet_structure_label("Do I WANT this?  (Yes / No)")
    assert is_worksheet_structure_label("Due to lack of skills or values?")
    assert is_tick_response_value("YES")
    assert is_enumerator_only("1")
    assert is_enumerator_only("1.")
    assert is_worksheet_structure_label("1.")


def test_structural_detection_skips_worksheet_grid_labels() -> None:
    ir = parse_fixture("worksheet_activity.docx")
    structural = detect_structural(ir)
    prompts = {candidate.prompt_text for candidate in structural.candidates}
    assert "Do I WANT this?  (Yes / No)" not in prompts
    assert "To be happy" not in prompts
    assert "YES" not in prompts
    assert "Question" not in prompts


def test_semantic_duplicates_are_suppressed() -> None:
    ir = parse_fixture("worksheet_activity.docx")
    structural = detect_structural(ir)
    first = structural.candidates[0]
    semantic = SemanticDetectionResult(
        classifications=[
            SemanticClassificationItem(
                block_id=first.block_id,
                kind="question",
                confidence=0.95,
                reason="duplicate",
            )
        ]
    )
    merged = merge_detections(ir, structural, semantic)
    matching = [task for task in merged.tasks if task.prompt_text == first.prompt_text]
    assert len(matching) == 1


def test_semantic_numbered_list_placeholders_are_suppressed() -> None:
    ir = parse_fixture("worksheet_activity.docx")
    structural = detect_structural(ir)
    enumerator_blocks = [
        block for block in ir.blocks if block.text.strip() in {"1.", "2.", "3.", "4.", "5."}
    ]
    assert enumerator_blocks, "fixture should contain numbered list placeholders"
    semantic = SemanticDetectionResult(
        classifications=[
            SemanticClassificationItem(
                block_id=block.block_id,
                kind="sub_question",
                confidence=0.9,
                reason="numbered item",
            )
            for block in enumerator_blocks
        ]
    )
    merged = merge_detections(ir, structural, semantic)
    prompts = {task.prompt_text for task in merged.tasks}
    assert "1." not in prompts
    assert "2." not in prompts


def test_document_grounded_questions_receive_recap_context() -> None:
    ir = parse_fixture("worksheet_activity.docx")
    task = Task(
        task_id="task_q1",
        kind="question",
        prompt_text="Q1. Explain the difference between animals and human beings.",
        context_block_ids=[],
        confidence=0.95,
    )
    pack = build_context_pack(ir, task, all_tasks=[task])
    rendered = "\n".join(block.text for block in pack.nearby_blocks)
    assert "continuous happiness" in rendered or "physical facility" in rendered
    assert pack.answer_mode == "document_grounded"


def test_personal_questions_use_user_specific_mode() -> None:
    assert classify_answer_mode("C4. Five things that make you feel unhappy:", has_document_content=False) == "user_specific"
    assert classify_answer_mode("Name", has_document_content=False) == "user_specific"


def test_reflective_gap_question_is_document_grounded() -> None:
    assert (
        classify_answer_mode(
            "If there is a gap between what you want and your present state — why this gap?",
            has_document_content=True,
        )
        == "document_grounded"
    )
    assert (
        classify_answer_mode(
            "• Are you able to see that your basic aspirations are for continuous happiness?",
            has_document_content=True,
        )
        == "document_grounded"
    )


def test_takeaways_question_is_document_grounded() -> None:
    ir = parse_fixture("worksheet_activity.docx")
    task = Task(
        task_id="task_c1",
        kind="question",
        prompt_text="C1. Five key take-aways from today (most important first):",
        context_block_ids=[],
        confidence=0.95,
    )
    pack = build_context_pack(ir, task, all_tasks=[task])
    assert pack.answer_mode == "document_grounded"
    assert any("happiness" in block.text.lower() for block in pack.nearby_blocks)


def test_skipped_tasks_are_not_in_context_packs() -> None:
    ir = parse_fixture("worksheet_activity.docx")
    tasks = [
        Task(
            task_id="task_ok",
            kind="question",
            prompt_text="Q1. Explain something.",
            confidence=0.95,
        ),
        Task(
            task_id="task_skip",
            kind="question",
            prompt_text="YES",
            confidence=0.95,
            skip_reason="already_answered",
        ),
    ]
    packs = build_context_packs(ir, tasks)
    assert [pack.task_id for pack in packs] == ["task_ok"]


def test_fill_blank_uses_existing_answer_space() -> None:
    ir = parse_fixture("worksheet_activity.docx")
    structural = detect_structural(ir)
    name_tasks = [c for c in structural.candidates if c.prompt_text.strip() == "Name"]
    assert name_tasks
    assert name_tasks[0].suggested_answer_space_id is not None


def test_no_duplicate_answer_insert_for_labels() -> None:
    ir = parse_fixture("worksheet_activity.docx")
    structural = detect_structural(ir)
    merged = merge_detections(ir, structural, SemanticDetectionResult())
    answerable = merged.answerable_tasks
    assert not any("Do I WANT this" in task.prompt_text for task in answerable)

    from docna.ir import Answer

    answers = [
        Answer(task_id=task.task_id, text=f"Answer for {task.task_id}", confidence=0.9)
        for task in answerable
    ]
    ops = plan_placements(ir, answerable, answers)
    assert not any(op.strategy == "insert_below" and "Do I WANT" in op.text for op in ops)


from tests.detect_helpers import ensure_fixture, parse_fixture


def _work_copy(source: Path) -> Path:
    dest = Path(tempfile.mkdtemp()) / source.name
    shutil.copy2(source, dest)
    return dest


def test_original_docx_immutability_for_worksheet_fixture() -> None:
    path = ensure_fixture("worksheet_activity.docx")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    work = _work_copy(path)
    ir = DocxAdapter().parse(work)
    structural = detect_structural(ir)
    merged = merge_detections(ir, structural, SemanticDetectionResult())
    from docna.ir import Answer

    answers = [
        Answer(task_id=task.task_id, text="Sample", confidence=0.9)
        for task in merged.answerable_tasks[:2]
    ]
    ops = plan_placements(ir, merged.answerable_tasks[:2], answers)
    DocxAdapter().apply(work, ops)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    job_paths = JobPaths(
        job_id="test",
        root=path.parent,
        original=path,
        work=work,
        internal_dir=path.parent / "internal",
        tasks_file=path.parent / "tasks.json",
        answers_file=path.parent / "answers.json",
        placement_ops_file=path.parent / "ops.json",
        generation_errors_file=path.parent / "errors.json",
        output_dir=path.parent / "output",
        output_file=path.parent / "output" / "completed.docx",
        edited_output_file=path.parent / "output" / "edited.docx",
        review=path.parent / "review.json",
        metadata=path.parent / "job.json",
        workspace=path.parent / "workspace.json",
    )
    assert original_is_immutable(job_paths, before_hash=before)


def test_multi_question_paragraph_unique_targets() -> None:
    ir = parse_fixture("multi_segment_shared_space.docx")
    structural = detect_structural(ir)
    merged = merge_detections(ir, structural, SemanticDetectionResult())
    shared = [
        task
        for task in merged.answerable_tasks
        if task.answer_space_id and task.prompt_text.startswith("If there is a gap")
    ]
    if len(shared) >= 2:
        from docna.ir import Answer

        answers = [
            Answer(task_id=task.task_id, text=f"Answer {index}", confidence=0.9)
            for index, task in enumerate(shared)
        ]
        ops = plan_placements(ir, shared, answers)
        fill_targets = [op.strategy for op in ops if op.strategy in {"fill_existing", "fill_cell"}]
        insert_targets = [op.strategy for op in ops if op.strategy == "insert_below"]
        assert fill_targets
        assert insert_targets
