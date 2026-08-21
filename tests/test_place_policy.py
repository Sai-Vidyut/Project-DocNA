"""Placement policy unit tests."""

from __future__ import annotations

from docna.ir import Answer, AnswerSpace, Block, Locator, Task
from docna.place.config import PlacementConfig
from docna.place.policy import evaluate_placement
from tests.helpers import opaque_locator, sample_block


def _task(**kwargs) -> Task:
    defaults = {
        "task_id": "task_0001",
        "kind": "question",
        "prompt_text": "What is your role?",
        "confidence": 0.95,
    }
    defaults.update(kwargs)
    return Task(**defaults)


def test_skip_instruction() -> None:
    decision = evaluate_placement(
        _task(kind="instruction", prompt_text="Complete all fields."),
        Answer(task_id="task_0001", text="ignored", confidence=1.0),
        answer_space=None,
        question_block=None,
        config=PlacementConfig(),
    )
    assert decision.strategy == "skip"
    assert "instruction" in decision.review_flags


def test_skip_already_answered_task() -> None:
    decision = evaluate_placement(
        _task(skip_reason="already_answered"),
        Answer(task_id="task_0001", text="New", confidence=1.0),
        answer_space=None,
        question_block=sample_block(),
        config=PlacementConfig(),
    )
    assert decision.strategy == "skip"
    assert "already_answered" in decision.review_flags


def test_skip_low_confidence() -> None:
    decision = evaluate_placement(
        _task(confidence=0.5),
        Answer(task_id="task_0001", text="Answer", confidence=1.0),
        answer_space=None,
        question_block=sample_block(),
        config=PlacementConfig(confidence_threshold=0.7),
    )
    assert decision.strategy == "skip"
    assert "low_confidence" in decision.review_flags


def test_fill_existing_for_blank_run() -> None:
    space = AnswerSpace(
        space_id="space_1",
        type="blank_run",
        locator=opaque_locator(),
        current_text="____",
        is_placeholder=True,
        capacity_hint=4,
    )
    decision = evaluate_placement(
        _task(answer_space_id="space_1"),
        Answer(task_id="task_0001", text="Ann", confidence=1.0),
        answer_space=space,
        question_block=sample_block(),
        config=PlacementConfig(),
    )
    assert decision.strategy == "fill_existing"


def test_insert_below_on_overflow() -> None:
    space = AnswerSpace(
        space_id="space_1",
        type="blank_run",
        locator=opaque_locator(),
        current_text="____",
        is_placeholder=True,
        capacity_hint=4,
    )
    block = sample_block()
    long_answer = "A" * 300
    decision = evaluate_placement(
        _task(answer_space_id="space_1"),
        Answer(task_id="task_0001", text=long_answer, confidence=1.0),
        answer_space=space,
        question_block=block,
        config=PlacementConfig(),
    )
    assert decision.strategy == "insert_below"
    assert "overflow" in decision.review_flags


def test_fill_cell_for_table_space() -> None:
    space = AnswerSpace(
        space_id="space_1",
        type="table_cell",
        locator=opaque_locator(),
        is_placeholder=True,
    )
    decision = evaluate_placement(
        _task(kind="table_item", answer_space_id="space_1"),
        Answer(task_id="task_0001", text="Paris", confidence=1.0),
        answer_space=space,
        question_block=None,
        config=PlacementConfig(),
    )
    assert decision.strategy == "fill_cell"


def test_insert_below_when_no_space() -> None:
    block = sample_block()
    decision = evaluate_placement(
        _task(),
        Answer(task_id="task_0001", text="Inheritance is...", confidence=1.0),
        answer_space=None,
        question_block=block,
        config=PlacementConfig(),
    )
    assert decision.strategy == "insert_below"
