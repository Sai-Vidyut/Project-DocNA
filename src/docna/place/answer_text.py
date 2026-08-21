"""Answer text splitting and output-presence checks shared by apply and validation."""

from __future__ import annotations

from docna.ir import PlacementOp


def split_answer_paragraphs(text: str) -> list[str]:
    """Split multi-paragraph answers the same way DOCX apply does."""
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    return chunks if chunks else [text.strip()]


def normalize_presence_text(text: str) -> str:
    """Collapse whitespace so paragraph boundaries do not break substring checks."""
    return " ".join(text.split())


def answer_text_present(op: PlacementOp, block_text: str) -> bool:
    """Return whether the placed answer text is present in reparsed document text."""
    text = op.text.strip()
    if not text:
        return True

    normalized_block = normalize_presence_text(block_text)
    if normalize_presence_text(text) in normalized_block:
        return True

    if text in block_text:
        return True

    chunks = split_answer_paragraphs(text)
    if not chunks:
        return True

    def chunk_present(chunk: str) -> bool:
        return chunk in block_text or normalize_presence_text(chunk) in normalized_block

    if op.strategy == "insert_below":
        first = chunks[0]
        if chunk_present(first):
            return all(chunk_present(chunk) for chunk in chunks[1:])

    return all(chunk_present(chunk) for chunk in chunks)
