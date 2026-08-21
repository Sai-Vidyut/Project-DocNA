"""IR model validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docna.ir import (
    Answer,
    AnswerSpace,
    Block,
    DocumentIR,
    Locator,
    PlacementOp,
    TableView,
    Task,
)
from tests.helpers import opaque_locator, sample_block, sample_document


def test_locator_accepts_arbitrary_adapter_payload() -> None:
    payload = {
        "kind": "run_range",
        "para_index": 4,
        "run_start": 2,
        "run_end": 5,
        "xpath": "//w:p[4]",
        "nested": {"sdt_id": 88, "flags": [True, False]},
    }
    locator = Locator(adapter="docx", payload=payload)
    assert locator.adapter == "docx"
    assert locator.payload == payload
    assert locator.payload is not payload


def test_locator_payload_is_opaque_dict() -> None:
    annotation = Locator.model_fields["payload"].annotation
    assert "dict" in str(annotation)


def test_locator_rejects_non_dict_payload() -> None:
    with pytest.raises(ValidationError):
        Locator(adapter="docx", payload=["not", "a", "dict"])  # type: ignore[arg-type]


def test_locator_rejects_empty_adapter() -> None:
    with pytest.raises(ValidationError):
        Locator(adapter="", payload={})


def test_locator_is_frozen() -> None:
    locator = opaque_locator(kind="paragraph")
    with pytest.raises(ValidationError):
        locator.adapter = "pdf"  # type: ignore[misc]


def test_block_validates() -> None:
    block = sample_block()
    assert block.kind == "paragraph"
    assert block.role_hint is None
    assert block.locator.adapter == "test-adapter"


@pytest.mark.parametrize(
    ("model", "field", "value"),
    [
        (Block, "kind", "chapter"),
        (AnswerSpace, "type", "highlight"),
        (DocumentIR, "source_format", "xlsx"),
        (Task, "kind", "heading"),
        (PlacementOp, "strategy", "overwrite"),
    ],
)
def test_invalid_enum_values_are_rejected(
    model: type[object],
    field: str,
    value: str,
) -> None:
    locator = opaque_locator()
    bases: dict[type[object], dict[str, object]] = {
        Block: {
            "block_id": "blk_1",
            "kind": "paragraph",
            "text": "x",
            "locator": locator,
        },
        AnswerSpace: {
            "space_id": "sp_1",
            "type": "none",
            "locator": locator,
        },
        DocumentIR: {
            "document_id": "doc_1",
            "source_format": "docx",
            "source_hash": "h",
        },
        Task: {
            "task_id": "t1",
            "kind": "question",
            "prompt_text": "Q?",
            "confidence": 1.0,
        },
        PlacementOp: {
            "op_id": "op_1",
            "task_id": "t1",
            "strategy": "skip",
        },
    }
    payload = dict(bases[model])
    payload[field] = value
    with pytest.raises(ValidationError):
        model.model_validate(payload)  # type: ignore[attr-defined]


def test_document_ir_validates_nested_tables_and_spaces() -> None:
    locator = opaque_locator(kind="cell", row=0, col=1)
    table = TableView(
        table_id="tbl_0",
        rows=[["blk_a", "blk_b"]],
        cell_locators={(0, 1): locator},
        header_row=True,
    )
    space = AnswerSpace(
        space_id="sp_1",
        type="table_cell",
        locator=locator,
        current_text="",
        is_placeholder=True,
        capacity_hint=40,
    )
    ir = DocumentIR(
        document_id="doc_1",
        source_format="docx",
        source_hash="deadbeef",
        blocks=[sample_block()],
        tables=[table],
        outline=[("blk_0001", "Applicant")],
        answer_spaces=[space],
        warnings=["headers_skipped"],
    )
    assert ir.tables[0].cell_locators[(0, 1)].adapter == "test-adapter"
    assert ir.answer_spaces[0].is_placeholder is True


def test_task_and_answer_validate() -> None:
    task = Task(
        task_id="t1",
        kind="sub_question",
        prompt_text="Date of birth?",
        parent_task_id="t0",
        context_block_ids=["blk_0001"],
        answer_space_id="sp_1",
        confidence=0.81,
        skip_reason=None,
    )
    answer = Answer(task_id="t1", text="1990-01-01", confidence=0.9, notes=None)
    assert task.parent_task_id == "t0"
    assert answer.task_id == task.task_id


def test_task_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        Task(
            task_id="t1",
            kind="question",
            prompt_text="Q?",
            confidence=1.5,
        )


def test_placement_op_carries_opaque_locator() -> None:
    target = Locator(
        adapter="docx",
        payload={"kind": "blank_run", "para_index": 12, "run_start": 3, "run_end": 4},
    )
    op = PlacementOp(
        op_id="op_1",
        task_id="t1",
        strategy="fill_existing",
        target=target,
        text="Jane Doe",
        style_clone_from=None,
        review_flags=["overflow"],
    )
    assert op.target == target
    assert op.target is not None
    assert op.target.adapter == "docx"
    dumped = op.model_dump()
    assert dumped["target"]["payload"]["para_index"] == 12


def test_placement_op_skip_allows_missing_target() -> None:
    op = PlacementOp(op_id="op_2", task_id="t2", strategy="skip", text="")
    assert op.target is None


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DocumentIR(
            document_id="doc_1",
            source_format="docx",
            source_hash="h",
            unknown_field=True,  # type: ignore[call-arg]
        )


def test_core_ir_has_no_docx_fields() -> None:
    assert "para_index" not in Locator.model_fields
    assert "xpath" not in Locator.model_fields
    assert "document_xml" not in DocumentIR.model_fields
    assert set(Locator.model_fields) == {"adapter", "payload"}
