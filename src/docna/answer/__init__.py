"""Answer generation: context packing and provider-backed answer creation."""

from docna.answer.config import ContextConfig
from docna.answer.context import build_context_pack, build_context_packs, render_context_for_prompt
from docna.answer.generate import generate_answers
from docna.answer.generation_config import GenerationConfig
from docna.answer.models import ContextPack, GenerationResult

__all__ = [
    "ContextConfig",
    "ContextPack",
    "GenerationConfig",
    "GenerationResult",
    "build_context_pack",
    "build_context_packs",
    "generate_answers",
    "render_context_for_prompt",
]
