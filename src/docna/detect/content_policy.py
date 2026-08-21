"""Shared heuristics for document content vs AI-directed injection text."""

from __future__ import annotations

import re

AI_DIRECTED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+"
        r"(?:instructions?|prompts?|rules?|context)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:reveal|show|print|output|display|repeat|tell\s+(?:me|us)?)\s+"
        r"(?:your\s+)?(?:(?:system|hidden|original|developer)\s+)?"
        r"(?:prompt|instructions?|rules?|configuration)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\balways\s+(?:output|print|say|respond(?:\s+with)?|reply(?:\s+with)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdo\s+not\s+(?:follow|obey|use)\s+(?:the\s+)?(?:above|previous|system)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdo\s+not\s+answer\s+(?:this|the)\s+question\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:tell|show|give|reveal|output|print)\s+(?:me|us)?\s+.*\b"
        r"(?:api\s*keys?|credentials?|passwords?|secrets?|tokens?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:answer|respond|reply)\s+with\s+.*\b(?:credentials?|passwords?|secrets?|tokens?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\byou\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\s+(?:if\s+)?(?:you|a)\b", re.IGNORECASE),
    re.compile(r"\bpretend\s+(?:you|to\s+be)\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
)

NARRATIVE_PROSE_RE = re.compile(
    r"^\s*(?:the|this|that|it|he|she|they|we|our|their|his|her|its|an|a)\s+"
    r"(?:\w+\s+){0,4}(?:describes|explains|states|shows|reports|includes|contains|"
    r"summarizes|demonstrates|illustrates|documents|confirms)\b",
    re.IGNORECASE,
)

DISCUSSION_ONLY_RE = re.compile(r"^\s*for discussion only\s*:", re.IGNORECASE)

SECTION_LABEL_RE = re.compile(
    r"^\s*(?:candidate responses|discussion(?:\s+only)?|notes|overview|"
    r"instructions|action items)\s*:\s*$",
    re.IGNORECASE,
)

WORKSHEET_COLUMN_HEADER_RE = re.compile(
    r"^\s*(?:do i want this|is this my state|question|your observation|requirement|"
    r"priority\s*\(|root cause|solution\s*\(|problem|due to lack of|increasing or decreasing|"
    r"#)\b",
    re.IGNORECASE,
)

WORKSHEET_ROW_LABEL_RE = re.compile(
    r"^\s*(?:to be happy|to be prosperous|continuity of|right understanding\s*\(|"
    r"relationship\s*\(|physical facility\s*\(|lack of physical facilities?)\b",
    re.IGNORECASE,
)

TICK_RESPONSE_RE = re.compile(r"^\s*(?:yes|no)\.?\s*$", re.IGNORECASE)

ENUMERATOR_ONLY_RE = re.compile(r"^\s*\d+\.?\s*$")

SHORT_HEADER_FRAGMENT_RE = re.compile(
    r"^\s*(?:why|what|how|which|when|where|who)\??\s*$",
    re.IGNORECASE,
)

PERSONAL_TASK_RE = re.compile(
    r"\b(?:your|my|you notice|you feel|your family|your view|your observation|"
    r"give you happiness|make you feel)\b",
    re.IGNORECASE,
)

DOCUMENT_GROUNDED_TASK_RE = re.compile(
    r"^\s*(?:Q\d+[\.\):]|C\d+[\.\)]|explain|describe|distinguish|what is meant|"
    r"take-aways|takeaways|holistic development|animal consciousness|human consciousness)",
    re.IGNORECASE,
)

FORM_PERSONAL_FIELD_RE = re.compile(
    r"^\s*(?:name|date|reg\.?\s*no|branch\s*/?\s*sec|signature|email|phone|address)\b",
    re.IGNORECASE,
)

RECAP_SECTION_RE = re.compile(
    r"^\s*(?:part\s+[a-z0-9—–-]+|key ideas|recap|session learning outcomes|"
    r"learning outcomes)\b",
    re.IGNORECASE,
)

FULL_WH_QUESTION_RE = re.compile(
    r"^\s*(?:what|how|why|when|where|who|which)\s+"
    r"(?:is|are|was|were|do|does|did|can|could|should|would|will)\b.+\?\s*$",
    re.IGNORECASE,
)


def looks_like_ai_directed_text(text: str) -> bool:
    """Return True when text appears to manipulate the AI rather than the document reader."""
    stripped = text.strip()
    if not stripped:
        return False
    return any(pattern.search(stripped) for pattern in AI_DIRECTED_PATTERNS)


def looks_like_narrative_prose(text: str) -> bool:
    """Return True when text reads as descriptive prose rather than a user task."""
    stripped = text.strip()
    if not stripped:
        return False
    if NARRATIVE_PROSE_RE.match(stripped):
        return True
    if stripped.endswith(".") and not stripped.endswith("?"):
        lowered = stripped.lower()
        if lowered.startswith(("the ", "this ", "that ", "it ", "an example")):
            return True
    return False


def is_discussion_only_marker(text: str) -> bool:
    stripped = text.strip()
    match = DISCUSSION_ONLY_RE.match(stripped)
    if not match:
        return False
    remainder = stripped[match.end() :].strip()
    return not remainder


def is_section_label_line(text: str) -> bool:
    return bool(SECTION_LABEL_RE.match(text.strip()))


def normalize_prompt_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def is_tick_response_value(text: str) -> bool:
    return bool(TICK_RESPONSE_RE.match(text.strip()))


def is_enumerator_only(text: str) -> bool:
    return bool(ENUMERATOR_ONLY_RE.match(text.strip()))


def is_worksheet_structure_label(text: str) -> bool:
    """Return True when text is a worksheet/table label or header, not an answerable task."""
    stripped = text.strip()
    if not stripped:
        return False
    if is_section_label_line(stripped):
        return True
    if WORKSHEET_COLUMN_HEADER_RE.match(stripped):
        return True
    if WORKSHEET_ROW_LABEL_RE.match(stripped):
        return True
    if SHORT_HEADER_FRAGMENT_RE.match(stripped):
        return True
    if is_tick_response_value(stripped):
        return True
    if is_enumerator_only(stripped):
        return True
    if stripped in {"#", "Question", "Your observation", "Requirement", "Problem", "Why?"}:
        return True
    if re.match(r"^\s*Priority\s*\(", stripped, re.IGNORECASE):
        return True
    if re.match(r"^\s*(?:Root cause|Solution)\s*\(", stripped, re.IGNORECASE):
        return True
    if stripped.endswith("?"):
        word_count = len(stripped.split())
        if word_count <= 3 and SHORT_HEADER_FRAGMENT_RE.match(stripped):
            return True
        if word_count <= 4 and re.match(
            r"^\s*(?:due to|increasing or)\b", stripped, re.IGNORECASE
        ):
            return True
    return False


def classify_answer_mode(task_text: str, *, has_document_content: bool) -> str:
    """Classify how the answer generator should respond to this task."""
    stripped = task_text.strip()
    if FORM_PERSONAL_FIELD_RE.match(stripped):
        return "user_specific"
    if re.search(
        r"\b(you notice around you|give you happiness|make you feel unhappy|your family)\b",
        stripped,
        re.IGNORECASE,
    ):
        return "user_specific"
    if DOCUMENT_GROUNDED_TASK_RE.match(stripped):
        return "document_grounded"
    if re.search(
        r"\b(aspirations|natural acceptance|see that|gap between|present state)\b",
        stripped,
        re.IGNORECASE,
    ) and has_document_content:
        return "document_grounded"
    if PERSONAL_TASK_RE.search(stripped):
        return "user_specific"
    if has_document_content:
        return "document_grounded"
    return "example_response"


def is_recap_section_title(text: str) -> bool:
    return bool(RECAP_SECTION_RE.match(text.strip()))


def is_structural_exclusion_reason(reason: str) -> bool:
    """Return True when structural exclusion should block semantic-only task resurrection."""
    return reason in {
        "example_label",
        "example_reference",
        "example_sample",
        "answer_provided",
        "narrative_prose",
        "discussion_marker",
        "worksheet_label",
    }
