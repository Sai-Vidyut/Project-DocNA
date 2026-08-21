"""Generate answers through the AI provider port.

No format adapters, no placement logic, no DOCX access.
"""

from __future__ import annotations

import time
import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import ValidationError

from docna.ai.port import AIProvider, ChatMessage
from docna.ai.prompts.answer_generation import (
    ANSWER_GENERATION_SYSTEM_PROMPT,
    BATCH_ANSWER_GENERATION_SYSTEM_PROMPT,
    build_answer_user_prompt,
    build_batch_answer_user_prompt,
)
from docna.answer.context import render_context_for_prompt
from docna.answer.generation_config import GenerationConfig
from docna.answer.models import (
    AnswerGenerationItem,
    AnswerGenerationResponse,
    BatchAnswerGenerationResponse,
    ContextPack,
    GenerationError,
    GenerationResult,
)
from docna.answer.text import prepare_model_answer_text
from docna.ir import Answer

RETRYABLE_ERROR_MARKERS = (
    "timeout",
    "rate limit",
    "ratelimit",
    "temporarily unavailable",
    "service unavailable",
    "connection reset",
    "connection error",
)

RETRYABLE_ANSWER_ERRORS = frozenset(
    {
        "empty_answer",
        "validation_error",
        "task_id_mismatch",
        "unexpected_response",
        "missing_answer",
        "duplicate_answer",
    }
)


def generate_answers(
    context_packs: Sequence[ContextPack],
    provider: AIProvider,
    *,
    config: GenerationConfig | None = None,
) -> GenerationResult:
    """Generate answers for context packs with batching, concurrency, and retries."""
    config = config or GenerationConfig()
    if not context_packs:
        return GenerationResult()

    answers: list[Answer] = []
    errors: list[GenerationError] = []
    warnings: list[str] = []

    seen_task_ids: set[str] = set()
    packs_to_process: list[ContextPack] = []
    for pack in context_packs:
        if pack.task_id in seen_task_ids:
            errors.append(
                GenerationError(
                    task_id=pack.task_id,
                    error_type="duplicate_task_id",
                    message=f"Duplicate context pack for task_id {pack.task_id!r}",
                )
            )
            continue
        seen_task_ids.add(pack.task_id)
        packs_to_process.append(pack)

    if not packs_to_process:
        return GenerationResult(answers=answers, errors=errors, warnings=warnings)

    batches = _chunk_packs(packs_to_process, config.batch_size)
    with ThreadPoolExecutor(max_workers=config.max_concurrency) as executor:
        futures = {
            executor.submit(_process_batch, batch, provider, config): batch
            for batch in batches
        }
        for future in as_completed(futures):
            batch = futures[future]
            try:
                batch_answers, batch_warnings, batch_errors = future.result()
            except Exception as exc:  # noqa: BLE001
                for pack in batch:
                    errors.append(
                        GenerationError(
                            task_id=pack.task_id,
                            error_type=type(exc).__name__,
                            message=str(exc),
                        )
                    )
                continue

            answers.extend(batch_answers)
            warnings.extend(batch_warnings)
            errors.extend(batch_errors)

    answers.sort(key=lambda item: item.task_id)
    return GenerationResult(answers=answers, errors=errors, warnings=warnings)


def _chunk_packs(packs: Sequence[ContextPack], batch_size: int) -> list[list[ContextPack]]:
    size = max(1, batch_size)
    return [list(packs[index : index + size]) for index in range(0, len(packs), size)]


def _process_batch(
    packs: Sequence[ContextPack],
    provider: AIProvider,
    config: GenerationConfig,
) -> tuple[list[Answer], list[str], list[GenerationError]]:
    if len(packs) == 1:
        answer, warnings, error = _generate_one(packs[0], provider, config)
        answers = [answer] if answer is not None else []
        errors = [error] if error is not None else []
        return answers, warnings, errors

    try:
        return _generate_batch(packs, provider, config)
    except _BatchGenerationFailure:
        if len(packs) == 1:
            answer, warnings, error = _generate_one(packs[0], provider, config)
            answers = [answer] if answer is not None else []
            errors = [error] if error is not None else []
            return answers, warnings, errors

        midpoint = len(packs) // 2
        left_answers, left_warnings, left_errors = _process_batch(
            packs[:midpoint], provider, config
        )
        right_answers, right_warnings, right_errors = _process_batch(
            packs[midpoint:], provider, config
        )
        return (
            left_answers + right_answers,
            left_warnings + right_warnings,
            left_errors + right_errors,
        )


class _BatchGenerationFailure(Exception):
    """Raised when a batched provider call cannot be recovered via retries."""


def _generate_batch(
    packs: Sequence[ContextPack],
    provider: AIProvider,
    config: GenerationConfig,
) -> tuple[list[Answer], list[str], list[GenerationError]]:
    messages = [
        ChatMessage(role="system", content=BATCH_ANSWER_GENERATION_SYSTEM_PROMPT),
        ChatMessage(role="user", content=build_batch_answer_user_prompt(packs)),
    ]
    expected_ids = [pack.task_id for pack in packs]

    last_errors: list[GenerationError] = []
    for attempt in range(config.max_retries + 1):
        try:
            response = provider.complete(messages, BatchAnswerGenerationResponse)
        except ValidationError as exc:
            _record_retry(config, attempt)
            last_errors = [
                GenerationError(
                    task_id=pack.task_id,
                    error_type="validation_error",
                    message=str(exc.errors()[0]["type"] if exc.errors() else "validation_error"),
                )
                for pack in packs
            ]
            if attempt < config.max_retries:
                if config.retry_backoff_seconds:
                    time.sleep(config.retry_backoff_seconds)
                continue
            raise _BatchGenerationFailure from exc
        except Exception as exc:  # noqa: BLE001
            _record_retry(config, attempt)
            if attempt < config.max_retries and _is_retryable(str(exc)):
                if config.retry_backoff_seconds:
                    time.sleep(config.retry_backoff_seconds)
                continue
            raise _BatchGenerationFailure from exc

        answers, warnings, errors = _validate_batch_response(expected_ids, response)
        retryable_errors = [
            error for error in errors if error.error_type in RETRYABLE_ANSWER_ERRORS
        ]
        if retryable_errors and not answers and attempt < config.max_retries:
            _record_retry(config, attempt)
            last_errors = errors
            if config.retry_backoff_seconds:
                time.sleep(config.retry_backoff_seconds)
            continue

        recovered_answers, recovered_warnings, recovered_errors = _retry_missing_tasks(
            packs,
            provider,
            config,
            answers,
            errors,
        )
        return (
            recovered_answers,
            warnings + recovered_warnings,
            recovered_errors,
        )

    if last_errors:
        raise _BatchGenerationFailure(str(last_errors[0].message))
    raise _BatchGenerationFailure("batch generation failed")


def _retry_missing_tasks(
    packs: Sequence[ContextPack],
    provider: AIProvider,
    config: GenerationConfig,
    answers: list[Answer],
    errors: list[GenerationError],
) -> tuple[list[Answer], list[str], list[GenerationError]]:
    answered_ids = {answer.task_id for answer in answers}
    failed_ids = {error.task_id for error in errors}
    missing_ids = {pack.task_id for pack in packs} - answered_ids - failed_ids
    retry_ids = failed_ids | missing_ids
    if not retry_ids:
        return answers, [], errors

    recovered_answers = list(answers)
    recovered_errors = [error for error in errors if error.task_id not in retry_ids]
    recovered_warnings: list[str] = []
    packs_by_id = {pack.task_id: pack for pack in packs}

    for task_id in sorted(retry_ids):
        pack = packs_by_id[task_id]
        answer, warnings, error = _generate_one(pack, provider, config)
        recovered_warnings.extend(warnings)
        if answer is not None:
            recovered_answers.append(answer)
        elif error is not None:
            recovered_errors.append(error)

    recovered_answers.sort(key=lambda item: item.task_id)
    return recovered_answers, recovered_warnings, recovered_errors


def _generate_one(
    pack: ContextPack,
    provider: AIProvider,
    config: GenerationConfig,
) -> tuple[Answer | None, list[str], GenerationError | None]:
    context_text = render_context_for_prompt(pack)
    messages = [
        ChatMessage(role="system", content=ANSWER_GENERATION_SYSTEM_PROMPT),
        ChatMessage(
            role="user",
            content=build_answer_user_prompt(context_text, pack.task_id),
        ),
    ]

    last_error: GenerationError | None = None
    for attempt in range(config.max_retries + 1):
        try:
            response = provider.complete(messages, AnswerGenerationResponse)
        except ValidationError as exc:
            _record_retry(config, attempt)
            last_error = GenerationError(
                task_id=pack.task_id,
                error_type="validation_error",
                message=str(exc.errors()[0]["type"] if exc.errors() else "validation_error"),
            )
            if attempt < config.max_retries:
                if config.retry_backoff_seconds:
                    time.sleep(config.retry_backoff_seconds)
                continue
            return None, [], last_error
        except Exception as exc:  # noqa: BLE001
            _record_retry(config, attempt)
            last_error = GenerationError(
                task_id=pack.task_id,
                error_type=type(exc).__name__,
                message=str(exc),
            )
            if attempt < config.max_retries and _is_retryable(str(exc)):
                if config.retry_backoff_seconds:
                    time.sleep(config.retry_backoff_seconds)
                continue
            return None, [], last_error

        answer, pack_warnings, pack_error = _validate_response(pack.task_id, response)
        if pack_error is None:
            return answer, pack_warnings, None
        if attempt < config.max_retries and pack_error.error_type in RETRYABLE_ANSWER_ERRORS:
            _record_retry(config, attempt)
            last_error = pack_error
            if config.retry_backoff_seconds:
                time.sleep(config.retry_backoff_seconds)
            continue
        return answer, pack_warnings, pack_error

    return None, [], last_error


def _validate_batch_response(
    expected_task_ids: Sequence[str],
    response: object,
) -> tuple[list[Answer], list[str], list[GenerationError]]:
    if not isinstance(response, BatchAnswerGenerationResponse):
        return [], [], [
            GenerationError(
                task_id=task_id,
                error_type="unexpected_response",
                message="Provider returned an unexpected response type",
            )
            for task_id in expected_task_ids
        ]

    answers: list[Answer] = []
    warnings: list[str] = []
    errors: list[GenerationError] = []
    seen_ids: set[str] = set()
    items_by_id: dict[str, AnswerGenerationItem] = {}

    for item in response.answers:
        if item.task_id in seen_ids:
            errors.append(
                GenerationError(
                    task_id=item.task_id,
                    error_type="duplicate_answer",
                    message=f"Model returned duplicate answer for task_id {item.task_id!r}",
                )
            )
            items_by_id.pop(item.task_id, None)
            continue
        seen_ids.add(item.task_id)
        items_by_id[item.task_id] = item

    for task_id in expected_task_ids:
        item = items_by_id.get(task_id)
        if item is None:
            errors.append(
                GenerationError(
                    task_id=task_id,
                    error_type="missing_answer",
                    message="Model did not return an answer for this task",
                )
            )
            continue
        answer, item_warnings, item_error = _validate_item(task_id, item)
        warnings.extend(item_warnings)
        if item_error is not None:
            errors.append(item_error)
        elif answer is not None:
            answers.append(answer)

    return answers, warnings, errors


def _validate_response(
    expected_task_id: str,
    response: object,
) -> tuple[Answer | None, list[str], GenerationError | None]:
    if not isinstance(response, AnswerGenerationResponse):
        return None, [], GenerationError(
            task_id=expected_task_id,
            error_type="unexpected_response",
            message="Provider returned an unexpected response type",
        )

    return _validate_item(expected_task_id, response.answer)


def _validate_item(
    expected_task_id: str,
    item: AnswerGenerationItem,
) -> tuple[Answer | None, list[str], GenerationError | None]:
    warnings: list[str] = []

    if item.task_id != expected_task_id:
        return None, [], GenerationError(
            task_id=expected_task_id,
            error_type="task_id_mismatch",
            message=f"Model returned task_id {item.task_id!r}",
        )

    if not item.text.strip():
        return None, [], GenerationError(
            task_id=expected_task_id,
            error_type="empty_answer",
            message="Model returned an empty answer",
        )

    if item.confidence < 0.70:
        warnings.append(f"low_confidence:{expected_task_id}:{item.confidence:.2f}")
    elif item.confidence < 0.90:
        warnings.append(f"review_recommended:{expected_task_id}:{item.confidence:.2f}")

    if re.search(r"\bblk_\d{4}\b", item.text) or re.search(r"\(\s*blk_\d{4}\s*\)", item.text):
        warnings.append(f"internal_locator_leak:{expected_task_id}")

    prepared = prepare_model_answer_text(item.text)

    return (
        Answer(
            task_id=item.task_id,
            text=prepared,
            confidence=item.confidence,
            notes=item.notes,
        ),
        warnings,
        None,
    )


def _record_retry(config: GenerationConfig, attempt: int) -> None:
    if config.metrics is None or attempt <= 0:
        return
    if config.metrics.calls:
        config.metrics.calls[-1].retry_attempt = attempt


def _is_retryable(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in RETRYABLE_ERROR_MARKERS)
