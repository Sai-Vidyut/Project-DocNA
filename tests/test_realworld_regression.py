"""Regression tests from real-world DOCX validation."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest
from docx import Document

from docna.adapters.docx import DocxAdapter
from docna.config import Settings
from docna.detect.run import detect_from_adapter
from docna.pipeline import run_job
from docna.storage.jobs import JobStore
from tests.pipeline_helpers import pipeline_mock_provider
from tests.realworld_helpers import ensure_all_realworld_fixtures, ensure_realworld_fixture
from tests.validation_harness import run_fixture


@pytest.fixture(scope="session")
def realworld_fixtures() -> list[Path]:
    return ensure_all_realworld_fixtures()


@pytest.fixture
def job_store(tmp_path: Path) -> JobStore:
    return JobStore(tmp_path / "jobs")


def test_all_realworld_fixtures_complete_pipeline(
    realworld_fixtures: list[Path], tmp_path: Path
) -> None:
    assert len(realworld_fixtures) == 18
    for fixture in realworld_fixtures:
        report = run_fixture(fixture, tmp_path / fixture.stem)
        assert report.original_unchanged, f"Original mutated: {fixture.name}"
        assert report.output_opens, f"Output corrupt: {fixture.name}"
        assert report.status == "completed", f"Pipeline failed: {fixture.name} {report.errors}"
        assert not report.errors, f"Validation errors in {fixture.name}: {report.errors}"


def test_examples_not_answered_detects_exercises_not_examples() -> None:
    path = ensure_realworld_fixture("examples_not_answered.docx")
    ir = DocxAdapter().parse(path)
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    prompts = [task.prompt_text for task in result.tasks]
    assert len([t for t in result.tasks if t.kind == "question"]) == 3
    assert any("Exercise 1" in text for text in prompts)
    assert any("Exercise 2" in text for text in prompts)
    assert any("Exercise 3" in text for text in prompts)
    assert not any(text.startswith("Example:") for text in prompts)
    assert not any(text.startswith("Thesis:") for text in prompts)


def test_programming_assignment_detects_numbered_imperatives_not_example() -> None:
    path = ensure_realworld_fixture("programming_assignment.docx")
    ir = DocxAdapter().parse(path)
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    prompts = [task.prompt_text for task in result.tasks]
    assert any("Implement a function" in text for text in prompts)
    assert any("Explain the difference" in text for text in prompts)
    assert any("Write pseudocode" in text for text in prompts)
    assert any("Bonus:" in text for text in prompts)
    assert not any(text.startswith("Question: What is Big-O") for text in prompts)


def test_instructions_mixed_questions_detects_all_four() -> None:
    path = ensure_realworld_fixture("instructions_mixed_questions.docx")
    ir = DocxAdapter().parse(path)
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    questions = [t for t in result.tasks if t.kind == "question"]
    assert len(questions) == 4
    space_ids = {task.answer_space_id for task in questions}
    assert len(space_ids) == 4


def test_mixed_fonts_each_question_gets_distinct_answer_space() -> None:
    path = ensure_realworld_fixture("mixed_fonts_styles.docx")
    ir = DocxAdapter().parse(path)
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    questions = [t for t in result.tasks if t.kind == "question"]
    space_ids = [task.answer_space_id for task in questions]
    assert len(questions) == 4
    assert len(set(space_ids)) == 4


def test_blank_lines_bind_spaces_sequentially() -> None:
    path = ensure_realworld_fixture("blank_lines.docx")
    ir = DocxAdapter().parse(path)
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    questions = [t for t in result.tasks if t.kind == "question"]
    space_ids = [task.answer_space_id for task in questions]
    assert len(questions) == 3
    assert len(set(space_ids)) == 3


def test_table_heavy_questionnaire_places_in_cells(tmp_path: Path) -> None:
    path = ensure_realworld_fixture("table_heavy_questionnaire.docx")
    report = run_fixture(path, tmp_path / "table_heavy")
    assert "fill_cell" in report.placement_strategies
    assert report.placement_strategies.get("fill_cell", 0) >= 3


def test_no_answer_spaces_uses_insert_below(tmp_path: Path) -> None:
    path = ensure_realworld_fixture("no_answer_spaces.docx")
    report = run_fixture(path, tmp_path / "no_spaces")
    assert report.answer_spaces == 0
    assert report.placement_strategies.get("insert_below", 0) == 3


def test_pipeline_original_immutability_via_job_store(
    job_store: JobStore, tmp_path: Path
) -> None:
    path = ensure_realworld_fixture("school_college_questionnaire.docx")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    paths = job_store.create_job(path.read_bytes(), path.name)
    settings = Settings.from_env(storage_dir=tmp_path / "jobs")
    result = run_job(job_store, paths, pipeline_mock_provider(), settings=settings)
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    assert before == after
    assert result.status == "completed"
    assert paths.output_file.exists()
    assert zipfile.is_zipfile(paths.output_file)
    Document(paths.output_file)


def test_insert_below_validation_accepts_answer_prefix(tmp_path: Path) -> None:
    path = ensure_realworld_fixture("consecutive_questions.docx")
    report = run_fixture(path, tmp_path / "consecutive")
    assert report.placement_strategies.get("insert_below", 0) == 4
    assert not report.errors
