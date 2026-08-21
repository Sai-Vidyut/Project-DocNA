"""Shared builders for Phase 1 tests."""

from __future__ import annotations

from docna.ir import Block, DocumentIR, Locator


def opaque_locator(**payload: object) -> Locator:
    return Locator(adapter="test-adapter", payload=dict(payload))


def sample_block(block_id: str = "blk_0001", text: str = "Name?") -> Block:
    return Block(
        block_id=block_id,
        kind="paragraph",
        text=text,
        locator=opaque_locator(kind="paragraph", index=0),
    )


def sample_document(*blocks: Block) -> DocumentIR:
    return DocumentIR(
        document_id="doc_1",
        source_format="docx",
        source_hash="abc123",
        blocks=list(blocks) if blocks else [sample_block()],
    )
