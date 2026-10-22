"""Interpret backend answers for the prompt-eval harness (eval headers, bodies, errors)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never, get_args

import httpx
from pydantic import ValidationError

from scripts.ai_prompt_eval.fixture_bank import (
    EditSuggestionFixture,
    InlineCompletionFixture,
    PromptEvalFixture,
)
from skriptoteket.protocols.llm import PromptEvalOutcome
from skriptoteket.web.api.v1.editor.models.responses import (
    EditorEditOpsResponse,
    EditorInlineCompletionResponse,
)

_OUTCOMES: tuple[PromptEvalOutcome, ...] = get_args(PromptEvalOutcome)


@dataclass(frozen=True)
class EvalMeta:
    """Prompt-composition metadata the backend returns in `X-Skriptoteket-Eval-*` headers."""

    template_id: str | None = None
    outcome: str | None = None
    system_prompt_chars: int | None = None
    prefix_chars: int | None = None
    suffix_chars: int | None = None
    instruction_chars: int | None = None
    selection_chars: int | None = None


@dataclass(frozen=True)
class ResponseSummary:
    """What the harness keeps of a 200 body: enablement and output size, never the text."""

    enabled: bool
    output_chars: int


def _coerce_int(value: str | None) -> int | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    try:
        return int(trimmed)
    except ValueError:
        return None


def _coerce_text(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()


def read_eval_meta_headers(headers: httpx.Headers) -> EvalMeta:
    return EvalMeta(
        template_id=_coerce_text(headers.get("X-Skriptoteket-Eval-Template-Id")),
        outcome=_coerce_text(headers.get("X-Skriptoteket-Eval-Outcome")),
        system_prompt_chars=_coerce_int(headers.get("X-Skriptoteket-Eval-System-Prompt-Chars")),
        prefix_chars=_coerce_int(headers.get("X-Skriptoteket-Eval-Prefix-Chars")),
        suffix_chars=_coerce_int(headers.get("X-Skriptoteket-Eval-Suffix-Chars")),
        instruction_chars=_coerce_int(headers.get("X-Skriptoteket-Eval-Instruction-Chars")),
        selection_chars=_coerce_int(headers.get("X-Skriptoteket-Eval-Selection-Chars")),
    )


def parse_error_meta(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        return {}

    if not isinstance(payload, dict):
        return {}

    meta: dict[str, object] = {}
    error = payload.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        if isinstance(code, str):
            meta["error_code"] = code

    correlation_id = payload.get("correlation_id")
    if isinstance(correlation_id, str):
        meta["correlation_id"] = correlation_id

    return meta


def read_outcome(*, meta: EvalMeta, response_chars: int, status_code: int) -> PromptEvalOutcome:
    if meta.outcome:
        for outcome in _OUTCOMES:
            if outcome == meta.outcome:
                return outcome
        return "error"

    if status_code != 200:
        return "error"

    return "ok" if response_chars else "empty"


def summarize_body(
    *, fixture: PromptEvalFixture, response: httpx.Response
) -> ResponseSummary | None:
    """Summarize a 200 body against the response model of the fixture's route, or None."""
    try:
        if isinstance(fixture, InlineCompletionFixture):
            completion = EditorInlineCompletionResponse.model_validate_json(response.content)
            return ResponseSummary(
                enabled=completion.enabled, output_chars=len(completion.completion)
            )
        if isinstance(fixture, EditSuggestionFixture):
            edit_ops = EditorEditOpsResponse.model_validate_json(response.content)
            patch_chars = sum(len(line) for op in edit_ops.ops for line in op.patch_lines)
            return ResponseSummary(enabled=edit_ops.enabled, output_chars=patch_chars)
    except ValidationError:
        return None
    assert_never(fixture)
