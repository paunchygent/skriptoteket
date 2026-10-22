"""Inline completion handler flow."""

from __future__ import annotations

import time
from collections.abc import Callable

import structlog
from structlog.contextvars import get_contextvars

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.llm_door import door_caller_for
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    InlineCompletionProviderProtocol,
    InlineCompletionResult,
    LLMCompletionResponse,
    PromptEvalMeta,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol

from .attempts import (
    InlineCompletionAttemptPlanner,
    PreparedAttempt,
    PromptTemplateError,
    elapsed_ms,
    try_complete,
)
from .capture import capture_inline_completion
from .normalization import normalize_inline_completion
from .telemetry import (
    build_eval_meta,
    log_inline_completion_normalized,
    log_inline_completion_truncated,
)

logger = structlog.get_logger(__name__)


class InlineCompletionFlow:
    def __init__(
        self,
        *,
        settings: Settings,
        provider: InlineCompletionProviderProtocol,
        capture_store: LlmCaptureStoreProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str, str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._provider = provider
        self._capture_store = capture_store
        self._attempts = InlineCompletionAttemptPlanner(
            settings=settings,
            token_counters=token_counters,
            system_prompt_loader=system_prompt_loader,
        )

    async def _finalize_response(
        self,
        *,
        attempt: PreparedAttempt,
        response: LLMCompletionResponse,
        actor: User,
        command: InlineCompletionCommand,
        prepare_ms: int | None,
        provider_ms: int | None,
        request_start: float,
        raw_correlation_id: object,
    ) -> InlineCompletionResult:
        raw_completion = response.completion or ""
        if response.finish_reason in ("length", "incomplete"):
            truncated_total_ms = elapsed_ms(request_start)
            log_inline_completion_truncated(
                attempt=attempt,
                finish_reason=response.finish_reason,
                raw_completion=raw_completion,
                prepare_ms=prepare_ms,
                provider_ms=provider_ms,
                total_ms=truncated_total_ms,
                user_id=str(actor.id),
            )

        normalize_start = time.perf_counter()
        normalized = normalize_inline_completion(
            completion=raw_completion,
            prefix=attempt.request.prefix,
            suffix=attempt.request.suffix,
        )
        normalize_ms = elapsed_ms(normalize_start)
        completion = normalized.completion
        total_ms = elapsed_ms(request_start)

        log_inline_completion_normalized(
            attempt=attempt,
            raw_completion=raw_completion,
            normalized_completion=completion,
            prefix_overlap_chars=normalized.prefix_overlap_chars,
            suffix_overlap_chars=normalized.suffix_overlap_chars,
            replace_suffix_chars=normalized.replace_suffix_chars,
            drop_reason=normalized.drop_reason,
            prepare_ms=prepare_ms,
            provider_ms=provider_ms,
            normalize_ms=normalize_ms,
            total_ms=total_ms,
            user_id=str(actor.id),
        )

        await capture_inline_completion(
            settings=self._settings,
            capture_store=self._capture_store,
            attempt=attempt,
            actor=actor,
            command=command,
            finish_reason=response.finish_reason,
            raw_completion=raw_completion,
            normalized=normalized,
            prepare_ms=prepare_ms,
            provider_ms=provider_ms,
            normalize_ms=normalize_ms,
            total_ms=total_ms,
            correlation_id=raw_correlation_id,
        )

        outcome = "ok" if completion else "empty"
        if response.finish_reason in ("length", "incomplete"):
            outcome = "truncated"
        return InlineCompletionResult(
            completion=completion,
            enabled=True,
            replace_suffix_chars=normalized.replace_suffix_chars or None,
            eval_meta=build_eval_meta(
                attempt=attempt,
                outcome=outcome,
                raw_chars=len(raw_completion),
                normalized_chars=len(completion),
                prefix_overlap_chars=normalized.prefix_overlap_chars,
                suffix_overlap_chars=normalized.suffix_overlap_chars,
                prepare_ms=prepare_ms,
                provider_ms=provider_ms,
                normalize_ms=normalize_ms,
                total_ms=total_ms,
            ),
        )

    async def handle(
        self,
        *,
        actor: User,
        command: InlineCompletionCommand,
    ) -> InlineCompletionResult:
        if not self._settings.LLM_COMPLETION_ENABLED:
            return InlineCompletionResult(
                completion="",
                enabled=False,
                eval_meta=PromptEvalMeta(
                    template_id=self._settings.LLM_COMPLETION_TEMPLATE_ID,
                    outcome="error",
                    system_prompt_chars=0,
                    prefix_chars=len(command.prefix),
                    suffix_chars=len(command.suffix),
                ),
            )

        request_start = time.perf_counter()
        raw_correlation_id = get_contextvars().get("correlation_id")

        template_id = self._settings.LLM_COMPLETION_TEMPLATE_ID

        try:
            prepare_start = time.perf_counter()
            attempt = self._attempts.prepare_attempt(
                prefix=command.prefix,
                suffix=command.suffix,
                active_file=command.active_file,
            )
            prepare_ms = elapsed_ms(prepare_start)
        except (OSError, PromptTemplateError):
            logger.warning("ai_completion_system_prompt_unavailable", template_id=template_id)
            return InlineCompletionResult(
                completion="",
                enabled=False,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="error",
                    system_prompt_chars=0,
                    prefix_chars=len(command.prefix),
                    suffix_chars=len(command.suffix),
                ),
            )

        logger.info(
            "ai_inline_completion_request",
            template_id=attempt.template_id,
            model=attempt.model,
            active_file=command.active_file,
            incoming_prefix_len=len(command.prefix),
            incoming_suffix_len=len(command.suffix),
            prefix_len=len(attempt.request.prefix),
            suffix_len=len(attempt.request.suffix),
            system_prompt_tokens=attempt.system_prompt_tokens,
            prefix_tokens=attempt.prefix_tokens,
            suffix_tokens=attempt.suffix_tokens,
            prompt_tokens_total=attempt.prompt_tokens_total,
            prompt_budget_tokens=attempt.prompt_budget_tokens,
            context_window_tokens=self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_COMPLETION_MAX_TOKENS,
            safety_margin_tokens=self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS,
            user_id=str(actor.id),
        )

        response, failure, provider_ms = await try_complete(
            provider=self._provider,
            request=attempt.request,
            system_prompt=attempt.system_prompt,
            caller=door_caller_for(user=actor),
        )

        if failure is not None:
            logger.info(
                "ai_inline_completion_failed",
                template_id=attempt.template_id,
                model=attempt.model,
                active_file=command.active_file,
                prefix_len=len(attempt.request.prefix),
                suffix_len=len(attempt.request.suffix),
                system_prompt_tokens=attempt.system_prompt_tokens,
                prefix_tokens=attempt.prefix_tokens,
                suffix_tokens=attempt.suffix_tokens,
                prompt_tokens_total=attempt.prompt_tokens_total,
                prompt_budget_tokens=attempt.prompt_budget_tokens,
                context_window_tokens=self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS,
                max_output_tokens=self._settings.LLM_COMPLETION_MAX_TOKENS,
                safety_margin_tokens=self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS,
                user_id=str(actor.id),
                outcome=failure.outcome,
                status_code=failure.status_code,
                prepare_ms=prepare_ms,
                provider_ms=provider_ms,
                total_ms=elapsed_ms(request_start),
            )
            return InlineCompletionResult(
                completion="",
                enabled=True,
                eval_meta=build_eval_meta(attempt=attempt, outcome=failure.outcome),
            )

        assert response is not None
        return await self._finalize_response(
            attempt=attempt,
            response=response,
            actor=actor,
            command=command,
            prepare_ms=prepare_ms,
            provider_ms=provider_ms,
            request_start=request_start,
            raw_correlation_id=raw_correlation_id,
        )


__all__ = ["InlineCompletionFlow"]
