"""Provider-agnostic structured completion port.

Phase 1 defines the contract only. No OpenAI, Azure, or Anthropic client is
connected here. Prompts live in ``docna.ai.prompts`` starting in Phase 5.
"""

from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """One chat turn sent to an AI provider."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class AIProvider(Protocol):
    """Structured-output completion. Implementations are added in Phase 5/6."""

    def complete(
        self,
        messages: Sequence[ChatMessage],
        response_schema: type[BaseModel],
    ) -> BaseModel:
        """Return an instance of ``response_schema``.

        Providers must not receive locator payloads or raw OOXML.
        """
        ...
