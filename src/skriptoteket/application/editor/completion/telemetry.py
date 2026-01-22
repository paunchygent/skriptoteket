"""Logging + evaluation metadata for inline completions."""

from __future__ import annotations

import structlog

from skriptoteket.protocols.llm import InlineCompletionProviderPreference, PromptEvalMeta

from .attempts import PreparedAttempt
from .normalization import DropReason

logger = structlog.get_logger(__name__)


def build_eval_meta(
    *,
    attempt: PreparedAttempt,
    outcome: str,
    raw_chars: int | None = None,
    normalized_chars: int | None = None,
    prefix_overlap_chars: int | None = None,
    suffix_overlap_chars: int | None = None,
    prepare_ms: int | None = None,
    provider_ms: int | None = None,
    normalize_ms: int | None = None,
    total_ms: int | None = None,
) -> PromptEvalMeta:
    return PromptEvalMeta(
        template_id=attempt.template_id,
        outcome=outcome,
        system_prompt_chars=len(attempt.system_prompt),
        system_prompt_tokens=attempt.system_prompt_tokens,
        prefix_chars=len(attempt.request.prefix),
        suffix_chars=len(attempt.request.suffix),
        prefix_tokens=attempt.prefix_tokens,
        suffix_tokens=attempt.suffix_tokens,
        prompt_tokens_total=attempt.prompt_tokens_total,
        prompt_budget_tokens=attempt.prompt_budget_tokens,
        raw_chars=raw_chars,
        normalized_chars=normalized_chars,
        prefix_overlap_chars=prefix_overlap_chars,
        suffix_overlap_chars=suffix_overlap_chars,
        prepare_ms=prepare_ms,
        provider_ms=provider_ms,
        normalize_ms=normalize_ms,
        total_ms=total_ms,
    )


def log_inline_completion_normalized(
    *,
    attempt: PreparedAttempt,
    provider_kind: InlineCompletionProviderPreference,
    raw_completion: str,
    normalized_completion: str,
    prefix_overlap_chars: int = 0,
    suffix_overlap_chars: int = 0,
    replace_suffix_chars: int = 0,
    drop_reason: DropReason | None = None,
    prepare_ms: int | None = None,
    provider_ms: int | None = None,
    normalize_ms: int | None = None,
    total_ms: int | None = None,
    user_id: str,
) -> None:
    logger.debug(
        "ai_inline_completion_normalized",
        template_id=attempt.template_id,
        provider_slot=attempt.slot,
        provider_kind=provider_kind,
        model=attempt.model,
        raw_chars=len(raw_completion),
        normalized_chars=len(normalized_completion),
        prefix_overlap_chars=prefix_overlap_chars,
        suffix_overlap_chars=suffix_overlap_chars,
        replace_suffix_chars=replace_suffix_chars,
        dropped=bool(raw_completion) and not normalized_completion,
        drop_reason=drop_reason,
        prepare_ms=prepare_ms,
        provider_ms=provider_ms,
        normalize_ms=normalize_ms,
        total_ms=total_ms,
        user_id=user_id,
    )


def log_inline_completion_truncated(
    *,
    attempt: PreparedAttempt,
    provider_kind: InlineCompletionProviderPreference,
    finish_reason: str | None,
    raw_completion: str,
    prepare_ms: int | None = None,
    provider_ms: int | None = None,
    total_ms: int | None = None,
    user_id: str,
) -> None:
    logger.debug(
        "ai_inline_completion_truncated",
        template_id=attempt.template_id,
        provider_slot=attempt.slot,
        provider_kind=provider_kind,
        model=attempt.model,
        finish_reason=finish_reason,
        raw_chars=len(raw_completion),
        prepare_ms=prepare_ms,
        provider_ms=provider_ms,
        total_ms=total_ms,
        user_id=user_id,
    )
