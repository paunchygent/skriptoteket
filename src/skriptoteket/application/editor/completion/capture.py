"""Capture storage for inline completion responses (dev-only)."""

from __future__ import annotations

from skriptoteket.application.editor.edit_ops.capture import resolve_capture_id
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.protocols.llm import InlineCompletionCommand
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol

from .attempts import PreparedAttempt, ProviderSlot
from .normalization import NormalizedInlineCompletion

_CAPTURE_PREFIX_TAIL_CHARS = 2_000
_CAPTURE_SUFFIX_HEAD_CHARS = 2_000


def _slot_kind(slot: ProviderSlot, *, primary_is_remote: bool, fallback_is_remote: bool) -> str:
    if slot == "primary":
        return "external" if primary_is_remote else "local"
    return "external" if fallback_is_remote else "local"


async def capture_inline_completion(
    *,
    settings: Settings,
    capture_store: LlmCaptureStoreProtocol,
    attempt: PreparedAttempt,
    actor: User,
    command: InlineCompletionCommand,
    finish_reason: str | None,
    raw_completion: str,
    normalized: NormalizedInlineCompletion,
    prepare_ms: int | None,
    provider_ms: int | None,
    normalize_ms: int | None,
    total_ms: int | None,
    correlation_id: object,
    primary_is_remote: bool,
    fallback_is_remote: bool,
) -> None:
    if settings.ENVIRONMENT == "production":
        return
    if not settings.LLM_CAPTURE_ON_SUCCESS_ENABLED:
        return
    if actor.role not in {Role.ADMIN, Role.SUPERUSER}:
        return
    capture_uuid = resolve_capture_id(raw_correlation_id=correlation_id)
    if capture_uuid is None:
        return

    prefix = attempt.request.prefix
    suffix = attempt.request.suffix
    prefix_tail = prefix[-_CAPTURE_PREFIX_TAIL_CHARS:]
    suffix_head = suffix[:_CAPTURE_SUFFIX_HEAD_CHARS]
    preview_prefix = prefix_tail[-200:]
    preview_suffix = suffix_head[:200]

    await capture_store.write_capture(
        kind="inline_completion_response",
        capture_id=capture_uuid,
        payload={
            "template_id": attempt.template_id,
            "provider_slot": attempt.slot,
            "provider_kind": _slot_kind(
                attempt.slot,
                primary_is_remote=primary_is_remote,
                fallback_is_remote=fallback_is_remote,
            ),
            "model": attempt.model,
            "active_file": command.active_file,
            "incoming_prefix_chars": len(command.prefix),
            "incoming_suffix_chars": len(command.suffix),
            "budgeted_prefix_chars": len(prefix),
            "budgeted_suffix_chars": len(suffix),
            "system_prompt_tokens": attempt.system_prompt_tokens,
            "prefix_tokens": attempt.prefix_tokens,
            "suffix_tokens": attempt.suffix_tokens,
            "prompt_tokens_total": attempt.prompt_tokens_total,
            "prompt_budget_tokens": attempt.prompt_budget_tokens,
            "context_window_tokens": settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS,
            "max_output_tokens": settings.LLM_COMPLETION_MAX_TOKENS,
            "safety_margin_tokens": settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS,
            "prefix_tail": prefix_tail,
            "suffix_head": suffix_head,
            "cursor_preview": f"{preview_prefix}<CURSOR>{preview_suffix}",
            "finish_reason": finish_reason,
            "raw_completion": raw_completion,
            "normalized_completion": normalized.completion,
            "dropped": bool(raw_completion) and not normalized.completion,
            "drop_reason": normalized.drop_reason,
            "prefix_overlap_chars": normalized.prefix_overlap_chars,
            "suffix_overlap_chars": normalized.suffix_overlap_chars,
            "replace_suffix_chars": normalized.replace_suffix_chars,
            "raw_chars": len(raw_completion),
            "normalized_chars": len(normalized.completion),
            "prepare_ms": prepare_ms,
            "provider_ms": provider_ms,
            "normalize_ms": normalize_ms,
            "total_ms": total_ms,
            "user_id": str(actor.id),
        },
    )
