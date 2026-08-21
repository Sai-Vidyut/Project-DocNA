"""Sanitization and classification helpers for user-facing answer text."""

from __future__ import annotations

import re

# Internal block references copied from prompt context — never user-facing.
_INTERNAL_BLOCK_REF_RE = re.compile(r"\(\s*blk_\d{4}\s*\)")

# Bare references when the model copies block ids without parentheses.
_INTERNAL_BLOCK_BARE_RE = re.compile(r"\bblk_\d{4}\b")


def is_user_input_placeholder(text: str | None) -> bool:
    """True when answer text is a placeholder requiring the user to respond."""
    normalized = (text or "").strip()
    if not normalized:
        return True
    lowered = normalized.lower().rstrip(".")
    if lowered == "[your response]" or lowered.startswith("[your response"):
        return True
    if lowered in {"user input required", "user input is required"}:
        return True
    if lowered in {"n/a", "na", "tbd", "to be completed"}:
        return True
    return False


def normalize_user_input_placeholder(text: str | None) -> str:
    """Normalize placeholders to the canonical review/export placeholder."""
    if is_user_input_placeholder(text):
        return "[Your response]"
    return (text or "").strip()


def sanitize_user_answer_text(text: str) -> str:
    """Remove internal block references from model-generated answer text."""
    cleaned = _INTERNAL_BLOCK_REF_RE.sub("", text)
    cleaned = _INTERNAL_BLOCK_BARE_RE.sub("", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" *\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r" +\n", "\n", cleaned)
    return cleaned.strip()


def prepare_model_answer_text(text: str) -> str:
    """Sanitize and normalize model output before persistence/placement."""
    cleaned = sanitize_user_answer_text(text.strip())
    if is_user_input_placeholder(cleaned):
        return "[Your response]"
    return cleaned
