"""Deterministic mock AI provider for tests."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from pydantic import BaseModel

from docna.ai.port import ChatMessage


class MockAIProvider:
    """Returns predefined structured responses without calling a real API."""

    def __init__(
        self,
        responder: Callable[[Sequence[ChatMessage], type[BaseModel]], BaseModel] | None = None,
        default_response: BaseModel | None = None,
    ) -> None:
        self._responder = responder
        self._default_response = default_response
        self.calls: list[tuple[Sequence[ChatMessage], type[BaseModel]]] = []

    def complete(
        self,
        messages: Sequence[ChatMessage],
        response_schema: type[BaseModel],
    ) -> BaseModel:
        self.calls.append((messages, response_schema))
        if self._responder is not None:
            return self._responder(messages, response_schema)
        if self._default_response is not None:
            if not isinstance(self._default_response, response_schema):
                raise TypeError(
                    f"Default response type {type(self._default_response)} "
                    f"does not match {response_schema}"
                )
            return self._default_response
        return _default_for_schema(response_schema)


def _default_for_schema(response_schema: type[BaseModel]) -> BaseModel:
    fields = getattr(response_schema, "model_fields", {})
    if "classifications" in fields:
        return response_schema.model_validate({"classifications": []})
    if "answers" in fields:
        return response_schema.model_validate({"answers": []})
    if "answer" in fields:
        return response_schema.model_validate(
            {
                "answer": {
                    "task_id": "task_0000",
                    "text": "Default mock answer.",
                    "confidence": 0.5,
                    "notes": None,
                }
            }
        )
    if "message" in fields:
        return response_schema.model_validate(
            {
                "message": "This question asks for your personal reflection based on the session.",
                "example_response": "Example: I notice increasing pressure on students.",
                "is_example": True,
            }
        )
    return response_schema.model_validate({})
