"""Phase 13 general detection robustness regression tests."""

from __future__ import annotations

from docna.adapters.docx import DocxAdapter
from docna.detect import detect_from_adapter
from docna.detect.structural import detect_structural
from tests.detect_helpers import parse_fixture, rule_based_mock_provider
from tests.helpers import sample_block, sample_document
from tests.pipeline_helpers import pipeline_mock_provider
from tests.realworld_helpers import ensure_realworld_fixture
from tests.stress_helpers import ensure_stress_fixture


def test_imperative_prompts_without_question_mark_are_detected() -> None:
    ir = DocxAdapter().parse(ensure_stress_fixture("interview_no_blanks.docx"))
    result = detect_structural(ir)
    prompts = [candidate.prompt_text for candidate in result.candidates]
    assert any("Describe a complex project" in text for text in prompts)
    assert any("prioritize conflicting deadlines" in text for text in prompts)
    assert any("failure and what you learned" in text for text in prompts)
    assert any("Why this organization" in text for text in prompts)


def test_prefixed_imperatives_are_detected() -> None:
    ir = DocxAdapter().parse(ensure_stress_fixture("performance_review_runs.docx"))
    result = detect_structural(ir)
    prompts = [candidate.prompt_text for candidate in result.candidates]
    assert len(prompts) >= 3
    assert any("revenue target" in text for text in prompts)
    assert any("leadership initiatives" in text for text in prompts)
    assert any("measurable" in text for text in prompts)


def test_narrative_imperatives_are_not_detected() -> None:
    ir = (
        parse_fixture("narrative_paragraphs.docx")
        if _fixture_exists("narrative_paragraphs.docx")
        else sample_document(
            sample_block(
                block_id="blk_0001",
                text="The report describes the meeting that occurred yesterday.",
            )
        )
    )
    result = detect_structural(ir)
    assert not result.candidates
    assert "blk_0001" in result.excluded_blocks


def test_multiple_tasks_in_one_paragraph_split_into_segments() -> None:
    ir = sample_document(
        sample_block(
            text="Describe your role. Explain your responsibilities. List your main achievements.",
        )
    )
    result = detect_structural(ir)
    prompts = [candidate.prompt_text for candidate in result.candidates]
    assert len(prompts) == 3
    assert prompts[0].startswith("Describe")
    assert prompts[1].startswith("Explain")
    assert prompts[2].startswith("List")


def test_discussion_only_marker_without_question_is_excluded() -> None:
    ir = sample_document(
        sample_block(block_id="blk_0001", text="For discussion only:"),
        sample_block(
            block_id="blk_0002",
            text="For discussion only: Should we change vendors?",
        ),
    )
    result = detect_structural(ir)
    prompts = [candidate.prompt_text for candidate in result.candidates]
    assert "blk_0001" in result.excluded_blocks
    assert any("Should we change vendors?" in text for text in prompts)


def test_already_answered_adjacent_paragraph_is_marked() -> None:
    ir = sample_document(
        sample_block(block_id="blk_0001", text="Have you read the policy?"),
        sample_block(block_id="blk_0002", text="Answer: Yes, on March 1."),
    )
    result = detect_from_adapter(ir, DocxAdapter(), rule_based_mock_provider())
    answered = [task for task in result.tasks if task.skip_reason == "already_answered"]
    assert len(answered) == 1
    assert "policy" in answered[0].prompt_text


def test_meta_instruction_not_detected_as_task() -> None:
    ir = DocxAdapter().parse(ensure_realworld_fixture("blank_lines.docx"))
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    prompts = [task.prompt_text for task in result.tasks if task.kind == "question"]
    assert not any("brief reflection for each prompt" in text.lower() for text in prompts)
    assert len(prompts) == 3


def test_wh_prompts_without_question_mark_in_dense_survey() -> None:
    ir = DocxAdapter().parse(ensure_stress_fixture("research_survey_dense.docx"))
    result = detect_from_adapter(ir, DocxAdapter(), pipeline_mock_provider())
    joined = " ".join(task.prompt_text for task in result.tasks)
    assert "statistical software" in joined.lower()
    assert "age range" in joined.lower()
    assert "recruiting diverse" in joined.lower()


def test_curated_realworld_regressions_still_hold() -> None:
    provider = pipeline_mock_provider()
    adapter = DocxAdapter()
    for fixture in (
        "prompt_injection.docx",
        "examples_not_answered.docx",
        "programming_assignment.docx",
        "school_college_questionnaire.docx",
    ):
        ir = adapter.parse(ensure_realworld_fixture(fixture))
        result = detect_from_adapter(ir, adapter, provider)
        assert result.tasks, fixture


def _fixture_exists(name: str) -> bool:
    from tests.detect_helpers import FIXTURE_DIR

    return (FIXTURE_DIR / name).exists()
