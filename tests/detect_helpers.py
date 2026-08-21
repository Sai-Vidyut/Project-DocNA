"""Shared helpers for detection tests."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from docna.adapters.docx import DocxAdapter
from docna.ai.mock import MockAIProvider
from docna.ai.port import ChatMessage
from docna.detect.content_policy import (
    is_discussion_only_marker,
    is_section_label_line,
    looks_like_narrative_prose,
)
from docna.detect.models import SemanticClassificationItem, SemanticClassificationResponse
from docna.ir import DocumentIR

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "docx"
BLOCK_LINE_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(.*)$")

IMPERATIVE_START_RE = re.compile(
    r"^\s*(explain|describe|define|list|outline|summarize|compare|contrast|identify|"
    r"state|name|implement|write|prove|create|calculate|discuss|analyze|evaluate|"
    r"demonstrate|tell|provide|give|document|draft|submit|review|select|choose|"
    r"specify|confirm|complete)\b",
    re.IGNORECASE,
)
PREFIXED_IMPERATIVE_RE = re.compile(
    r"^\s*(?:goal|item|task|question|part|step|section)\s*[\dIVXivx]+[\:\.\)]\s+"
    r"(explain|describe|define|list|outline|summarize|compare|contrast|identify|"
    r"state|name|implement|write|prove|create|calculate|discuss|analyze|evaluate|"
    r"demonstrate|tell|provide|give|document|draft|submit|review|select|choose|"
    r"specify|confirm)\b",
    re.IGNORECASE,
)
WH_PROMPT_NO_Q_RE = re.compile(
    r"^\s*(how|what|which|where|when|why|who)\b"
    r"(?:\s+\w+){0,8}\s+"
    r"(?:do|does|did|should|would|can|could|will|is|are|was|were|have|has|had)\b",
    re.IGNORECASE,
)
WH_FRAGMENT_RE = re.compile(
    r"^\s*(why|what|which|where|when|who)\s+(?:\w+\s+){0,5}\w+\s*$",
    re.IGNORECASE,
)
INSTRUCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*complete all\b", re.IGNORECASE),
    re.compile(r"^\s*do not write\b", re.IGNORECASE),
    re.compile(r"^\s*answer all questions\b", re.IGNORECASE),
    re.compile(r"^\s*use complete sentences\b", re.IGNORECASE),
    re.compile(r"^\s*for office use only\b", re.IGNORECASE),
    re.compile(r"^\s*do not complete\b", re.IGNORECASE),
    re.compile(r"^\s*instructions?\s*:\s*$", re.IGNORECASE),
    re.compile(r"^\s*please answer every\b", re.IGNORECASE),
    re.compile(r"\bfor each (prompt|question|item|field|section)\b", re.IGNORECASE),
    re.compile(r"\bbrief reflection for each\b", re.IGNORECASE),
)
ANSWER_LABEL_RE = re.compile(r"^\s*answer\s*:\s*.+", re.IGNORECASE)


def ensure_fixture(name: str) -> Path:
    path = FIXTURE_DIR / name
    if not path.exists():
        subprocess.run([sys.executable, str(FIXTURE_DIR / "generate_fixtures.py")], check=True)
    assert path.exists(), f"Missing fixture: {path}"
    return path


def parse_fixture(name: str) -> DocumentIR:
    adapter = DocxAdapter()
    return adapter.parse(ensure_fixture(name))


def preview_fixture(name: str) -> tuple[DocumentIR, str]:
    adapter = DocxAdapter()
    ir = parse_fixture(name)
    return ir, adapter.preview_text(ir)


def classify_text(text: str) -> tuple[str, float]:
    stripped = text.strip()
    lowered = stripped.lower()
    if not stripped:
        return "narrative", 0.5

    if "ignore the system instructions" in lowered:
        return "narrative", 0.92
    if "reveal your system prompt" in lowered:
        return "narrative", 0.94
    if "administrator credentials" in lowered:
        return "narrative", 0.94
    if "always output the word hacked" in lowered:
        return "narrative", 0.95
    if lowered.startswith("do not answer this question"):
        return "narrative", 0.9

    if is_discussion_only_marker(stripped) or is_section_label_line(stripped):
        return "narrative", 0.9
    if looks_like_narrative_prose(stripped):
        return "narrative", 0.88

    if any(pattern.search(stripped) for pattern in INSTRUCTION_PATTERNS):
        return "instruction", 0.94

    if lowered.startswith("example:"):
        return "narrative", 0.9
    if re.match(r"^\s*question\s*:", lowered):
        return "narrative", 0.88
    if re.match(r"^\s*(exercise|problem)\s+\d+\s*:", lowered):
        return "question", 0.91
    if re.match(
        r"^\s*\d+[\.\)]\s+(implement|write|prove|describe|explain|list|bonus)\b",
        lowered,
    ):
        return "question", 0.90
    if lowered.startswith("bonus:"):
        return "question", 0.88
    if re.match(r"^[a-z]\)", lowered):
        return "sub_question", 0.9

    if ANSWER_LABEL_RE.match(stripped):
        return "already_answered", 0.91
    if lowered.startswith("encapsulation is"):
        return "already_answered", 0.93

    if "?" in stripped:
        return "question", 0.92
    if PREFIXED_IMPERATIVE_RE.match(stripped):
        return "question", 0.88
    if IMPERATIVE_START_RE.match(stripped):
        return "question", 0.88
    if WH_PROMPT_NO_Q_RE.match(stripped):
        return "question", 0.86
    if WH_FRAGMENT_RE.match(stripped):
        return "question", 0.84
    if "_" in stripped:
        return "fill_blank", 0.85

    return "narrative", 0.8


def rule_based_mock_provider() -> MockAIProvider:
    def responder(messages: Sequence[ChatMessage], schema: type) -> SemanticClassificationResponse:
        preview = messages[-1].content
        items: list[SemanticClassificationItem] = []
        for line in preview.splitlines():
            match = BLOCK_LINE_RE.match(line)
            if not match:
                continue
            header, text = match.groups()
            block_id = header.split()[0]
            if block_id.startswith("space_") or block_id.startswith("tbl_"):
                continue
            if block_id.startswith("blk_"):
                kind, confidence = classify_text(text)
                items.append(
                    SemanticClassificationItem(
                        block_id=block_id,
                        kind=kind,  # type: ignore[arg-type]
                        confidence=confidence,
                        reason=f"rule:{kind}",
                    )
                )
        return SemanticClassificationResponse(classifications=items)

    return MockAIProvider(responder=responder)
