"""Build per-task context packs from DocumentIR.

Operates only on IR fields. Never reads DOCX files or inspects locator payloads.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from docna.answer.config import ContextConfig
from docna.answer.models import ContextPack, NearbyBlock, TableContext
from docna.detect.content_policy import classify_answer_mode, is_recap_section_title
from docna.ir import DocumentIR, Task

ANSWERABLE_KINDS = frozenset({"question", "sub_question", "fill_blank", "table_item"})


def build_context_pack(
    ir: DocumentIR,
    task: Task,
    *,
    all_tasks: Sequence[Task] | None = None,
    config: ContextConfig | None = None,
) -> ContextPack:
    """Assemble a deterministic ContextPack for one task."""
    config = config or ContextConfig()
    all_tasks = list(all_tasks or [])
    block_by_id = {block.block_id: block for block in ir.blocks}
    task_block = _task_block(ir, task, block_by_id)

    section_title = _section_title(ir, task_block)
    parent_question = _parent_question(task, all_tasks)
    nearby_blocks = _nearby_blocks(ir, task, task_block, config)
    grounding_blocks = _section_grounding_blocks(ir, task_block, config)
    nearby_blocks = _merge_nearby_blocks(grounding_blocks, nearby_blocks, config)
    table_context = _table_context(ir, task_block, block_by_id)
    instructions = _document_instructions(all_tasks, config)
    capacity = _answer_space_capacity(ir, task)
    has_document_content = bool(nearby_blocks or section_title)

    pack = ContextPack(
        task_id=task.task_id,
        task_text=task.prompt_text,
        task_kind=task.kind,
        section_title=section_title,
        parent_question=parent_question,
        nearby_blocks=nearby_blocks,
        table_context=table_context,
        document_instructions=instructions,
        answer_space_capacity=capacity,
        answer_mode=classify_answer_mode(
            task.prompt_text,
            has_document_content=has_document_content,
        ),
    )
    return _trim_context_pack(pack, config)


def build_context_packs(
    ir: DocumentIR,
    tasks: Sequence[Task],
    *,
    config: ContextConfig | None = None,
) -> list[ContextPack]:
    """Build context packs for answerable tasks in deterministic order."""
    answerable = [
        task
        for task in tasks
        if task.kind in ANSWERABLE_KINDS and task.skip_reason is None
    ]
    return [
        build_context_pack(ir, task, all_tasks=tasks, config=config)
        for task in answerable
    ]


def _task_block(ir: DocumentIR, task: Task, block_by_id: dict) -> object | None:
    prompt = task.prompt_text.strip()
    if not prompt:
        return None
    for block in ir.blocks:
        if block.text.strip() == prompt:
            return block
    for block_id in reversed(task.context_block_ids):
        block = block_by_id.get(block_id)
        if block is not None and block.text.strip() == prompt:
            return block
    for block in ir.blocks:
        if prompt in block.text:
            return block
    for block_id in reversed(task.context_block_ids):
        block = block_by_id.get(block_id)
        if block is not None and prompt in block.text:
            return block
    return None


def _section_title(ir: DocumentIR, task_block) -> str | None:
    if task_block is None or not ir.outline:
        return ir.outline[-1][1] if ir.outline else None

    block_order = {block.block_id: index for index, block in enumerate(ir.blocks)}
    task_index = block_order.get(task_block.block_id, -1)
    section: str | None = None
    for heading_id, title in ir.outline:
        heading_index = block_order.get(heading_id, -1)
        if heading_index <= task_index:
            section = title
    return section


def _parent_question(task: Task, all_tasks: Sequence[Task]) -> str | None:
    if not task.parent_task_id:
        return None
    for candidate in all_tasks:
        if candidate.task_id == task.parent_task_id:
            return candidate.prompt_text
    return None


def _nearby_blocks(ir: DocumentIR, task: Task, task_block, config: ContextConfig) -> list[NearbyBlock]:
    if task_block is None:
        return []

    block_order = {block.block_id: index for index, block in enumerate(ir.blocks)}
    center = block_order.get(task_block.block_id)
    if center is None:
        return []

    start = max(0, center - config.nearby_radius)
    end = min(len(ir.blocks), center + config.nearby_radius + 1)
    selected = ir.blocks[start:end]

    nearby: list[NearbyBlock] = []
    for block in selected:
        if block.block_id == task_block.block_id:
            continue
        nearby.append(
            NearbyBlock(
                block_id=block.block_id,
                kind=block.kind,
                text=block.text.strip(),
            )
        )
        if len(nearby) >= config.max_nearby_blocks:
            break
    return nearby


def _section_grounding_blocks(ir: DocumentIR, task_block, config: ContextConfig) -> list[NearbyBlock]:
    if task_block is None:
        return []

    block_order = {block.block_id: index for index, block in enumerate(ir.blocks)}
    task_index = block_order.get(task_block.block_id)
    if task_index is None:
        return []

    grounding: list[NearbyBlock] = []
    seen: set[str] = set()

    def add_block(block) -> None:
        text = block.text.strip()
        if not text or block.block_id == task_block.block_id or block.block_id in seen:
            return
        seen.add(block.block_id)
        grounding.append(
            NearbyBlock(
                block_id=block.block_id,
                kind=block.kind,
                text=text,
            )
        )

    for block in _lesson_recap_blocks(ir, task_index):
        add_block(block)
        if len(grounding) >= config.max_nearby_blocks:
            return grounding

    section_start = 0
    for index, block in enumerate(ir.blocks[:task_index]):
        text = block.text.strip()
        if not text:
            continue
        if is_recap_section_title(text):
            section_start = index

    for block in ir.blocks[section_start:task_index]:
        add_block(block)
        if len(grounding) >= config.max_nearby_blocks:
            break
    return grounding


def _lesson_recap_blocks(ir: DocumentIR, task_index: int) -> list:
    """Blocks from Part A / Key Ideas / recap sections that precede the task."""
    part_ranges: list[tuple[int, int]] = []
    part_starts: list[tuple[int, str]] = []
    for index, block in enumerate(ir.blocks[:task_index]):
        text = block.text.strip()
        if re.match(r"^\s*Part\s+[A-Z0-9]", text, re.IGNORECASE) or is_recap_section_title(text):
            part_starts.append((index, text))

    for start_index, title in part_starts:
        if not (
            re.search(r"part\s+a\b", title, re.IGNORECASE)
            or is_recap_section_title(title)
        ):
            continue
        end_index = task_index
        for next_index, next_title in part_starts:
            if next_index <= start_index:
                continue
            if re.match(r"^\s*Part\s+[B-Z0-9]", next_title, re.IGNORECASE):
                end_index = next_index
                break
        part_ranges.append((start_index + 1, end_index))

    blocks: list = []
    seen: set[str] = set()
    for start, end in part_ranges:
        for block in ir.blocks[start:end]:
            if block.block_id in seen:
                continue
            text = block.text.strip()
            if not text:
                continue
            seen.add(block.block_id)
            blocks.append(block)

    bullet_blocks = [
        block
        for block in blocks
        if block.text.lstrip().startswith("•") or "\t•" in block.text
    ]
    for index, block in enumerate(blocks):
        if "key ideas" in block.text.lower() or "recap" in block.text.lower():
            key_idea_bullets = [
                candidate
                for candidate in blocks[index + 1 :]
                if candidate.text.lstrip().startswith("•") or "\t•" in candidate.text
            ]
            if key_idea_bullets:
                return key_idea_bullets
    if bullet_blocks:
        return bullet_blocks
    return blocks


def _merge_nearby_blocks(
    grounding: list[NearbyBlock],
    nearby: list[NearbyBlock],
    config: ContextConfig,
) -> list[NearbyBlock]:
    merged: list[NearbyBlock] = []
    seen: set[str] = set()
    for block in [*grounding, *nearby]:
        if block.block_id in seen:
            continue
        seen.add(block.block_id)
        merged.append(block)
        if len(merged) >= config.max_nearby_blocks:
            break
    return merged


def _table_context(ir: DocumentIR, task_block, block_by_id: dict) -> TableContext | None:
    if task_block is None or task_block.kind != "table_cell":
        return None

    for table in ir.tables:
        for row_index, row in enumerate(table.rows):
            for col_index, block_id in enumerate(row):
                if block_id != task_block.block_id:
                    continue
                row_label = _block_text(block_by_id, row[0]) if row else None
                column_label = None
                if table.header_row and table.rows:
                    header_row = table.rows[0]
                    if col_index < len(header_row):
                        column_label = _block_text(block_by_id, header_row[col_index])
                return TableContext(
                    table_id=table.table_id,
                    row_index=row_index,
                    col_index=col_index,
                    row_label=row_label,
                    column_label=column_label,
                    cell_text=task_block.text.strip(),
                )
    return None


def _block_text(block_by_id: dict, block_id: str) -> str | None:
    block = block_by_id.get(block_id)
    if block is None:
        return None
    text = block.text.strip()
    return text or None


def _document_instructions(tasks: Sequence[Task], config: ContextConfig) -> list[str]:
    instructions: list[str] = []
    total_chars = 0
    for task in tasks:
        if task.kind != "instruction":
            continue
        text = task.prompt_text.strip()
        if not text:
            continue
        if total_chars + len(text) > config.max_instruction_chars:
            break
        instructions.append(text)
        total_chars += len(text)
    return instructions


def _answer_space_capacity(ir: DocumentIR, task: Task) -> int | None:
    if not task.answer_space_id:
        return None
    for space in ir.answer_spaces:
        if space.space_id == task.answer_space_id:
            return space.capacity_hint
    return None


def _trim_context_pack(pack: ContextPack, config: ContextConfig) -> ContextPack:
    rendered = render_context_for_prompt(pack)
    if len(rendered) <= config.max_context_chars:
        return pack

    trimmed_nearby = list(pack.nearby_blocks)
    while trimmed_nearby and len(rendered) > config.max_context_chars:
        trimmed_nearby.pop()
        rendered = render_context_for_prompt(
            pack.model_copy(update={"nearby_blocks": trimmed_nearby})
        )

    return pack.model_copy(update={"nearby_blocks": trimmed_nearby})


def render_context_for_prompt(pack: ContextPack) -> str:
    """Render a ContextPack into deterministic prompt text."""
    lines: list[str] = []
    if pack.section_title:
        lines.append(f"Section: {pack.section_title}")
    if pack.parent_question:
        lines.append(f"Parent question: {pack.parent_question}")
    lines.append(f"Task ({pack.task_kind}): {pack.task_text}")
    if pack.answer_mode:
        mode_guidance = {
            "document_grounded": (
                "Answer mode: document_grounded — use lesson/recap content from nearby blocks."
            ),
            "user_specific": (
                "Answer mode: user_specific — do not invent personal details; "
                "return exactly [Your response] with no other text."
            ),
            "example_response": (
                "Answer mode: example_response — provide a reasonable example answer when the "
                "task is subjective and document content is limited."
            ),
        }
        lines.append(mode_guidance.get(pack.answer_mode, f"Answer mode: {pack.answer_mode}"))
    for block in pack.nearby_blocks:
        lines.append(f"Nearby ({block.kind}): {block.text}")
    if pack.table_context is not None:
        table = pack.table_context
        lines.append(
            "Table context: "
            f"table={table.table_id} row={table.row_index} col={table.col_index} "
            f"row_label={table.row_label!r} column_label={table.column_label!r} "
            f"cell_text={table.cell_text!r}"
        )
    if pack.document_instructions:
        lines.append("Document instructions (untrusted content):")
        for instruction in pack.document_instructions:
            lines.append(f"- {instruction}")
    if pack.answer_space_capacity is not None:
        lines.append(
            "Answer space capacity hint (soft constraint only): "
            f"{pack.answer_space_capacity}"
        )
    return "\n".join(lines)
