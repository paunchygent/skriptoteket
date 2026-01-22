"""Inline completion handler flow."""

from __future__ import annotations

import time
from collections.abc import Callable

import structlog
from structlog.contextvars import get_contextvars

from skriptoteket.application.editor.remote_fallback import RemoteFallbackConsent
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    InlineCompletionProvidersProtocol,
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
    ProviderSlot,
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

REMOTE_FALLBACK_REQUIRED_NOTICE_CODE = "remote_fallback_required"
REMOTE_PROVIDERS_DISABLED_NOTICE_CODE = "remote_providers_disabled"

REMOTE_FALLBACK_REQUIRED_NOTICE_MESSAGE = (
    "Den lokala modellen för inline-completions är inte tillgänglig. "
    "Aktivera externa AI-API:er i Profil → AI-inställningar om du vill fortsätta få completions."
)
REMOTE_PROVIDERS_DISABLED_NOTICE_MESSAGE = (
    "Systemadministratören tillåter inte externa AI-modeller i den här miljön. "
    "Kontakta din administratör om du har frågor."
)


class InlineCompletionFlow:
    def __init__(
        self,
        *,
        settings: Settings,
        providers: InlineCompletionProvidersProtocol,
        capture_store: LlmCaptureStoreProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str, str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._providers = providers
        self._capture_store = capture_store
        self._attempts = InlineCompletionAttemptPlanner(
            settings=settings,
            providers=providers,
            token_counters=token_counters,
            system_prompt_loader=system_prompt_loader,
        )

    def _notice_for_remote_block(self) -> tuple[str, str]:
        if not self._settings.AI_REMOTE_PROVIDERS_ENABLED:
            return REMOTE_PROVIDERS_DISABLED_NOTICE_CODE, REMOTE_PROVIDERS_DISABLED_NOTICE_MESSAGE
        return REMOTE_FALLBACK_REQUIRED_NOTICE_CODE, REMOTE_FALLBACK_REQUIRED_NOTICE_MESSAGE

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
        provider_kind = self._attempts.slot_kind(attempt.slot)
        raw_completion = response.completion or ""
        if response.finish_reason in ("length", "incomplete"):
            truncated_total_ms = elapsed_ms(request_start)
            log_inline_completion_truncated(
                attempt=attempt,
                provider_kind=provider_kind,
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
            provider_kind=provider_kind,
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
            primary_is_remote=self._providers.primary_is_remote,
            fallback_is_remote=self._providers.fallback_is_remote,
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
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

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

        default_template_id = self._settings.LLM_COMPLETION_TEMPLATE_ID
        local_slot, external_slot = self._attempts.resolve_provider_slots()

        consent = RemoteFallbackConsent(
            allow_remote_fallback=command.allow_remote_fallback,
            remote_providers_enabled=self._settings.AI_REMOTE_PROVIDERS_ENABLED,
        )
        remote_allowed = consent.remote_allowed
        should_prompt_for_remote = consent.should_prompt

        preferred_kind = command.inline_completion_provider
        if preferred_kind is None:
            preferred_kind = "external" if remote_allowed and external_slot is not None else "local"

        primary_slot: ProviderSlot | None
        if preferred_kind == "external":
            primary_slot = (
                external_slot if external_slot is not None and remote_allowed else local_slot
            )
        else:
            primary_slot = (
                local_slot
                if local_slot is not None
                else (external_slot if external_slot is not None and remote_allowed else None)
            )

        if primary_slot is None:
            if external_slot is not None and not remote_allowed:
                if not self._settings.AI_REMOTE_PROVIDERS_ENABLED or should_prompt_for_remote:
                    notice_code, notice_message = self._notice_for_remote_block()
                    return InlineCompletionResult(
                        completion="",
                        enabled=True,
                        notice_message=notice_message,
                        notice_variant="warning",
                        notice_code=notice_code,
                        eval_meta=PromptEvalMeta(
                            template_id=default_template_id,
                            outcome="error",
                            system_prompt_chars=0,
                            prefix_chars=len(command.prefix),
                            suffix_chars=len(command.suffix),
                        ),
                    )

            return InlineCompletionResult(
                completion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=default_template_id,
                    outcome="error",
                    system_prompt_chars=0,
                    prefix_chars=len(command.prefix),
                    suffix_chars=len(command.suffix),
                ),
            )

        fallback_slot: ProviderSlot | None = None
        if self._providers.fallback is not None:
            fallback_slot = "fallback" if primary_slot == "primary" else "primary"

        primary_prepare_ms: int | None = None
        fallback_prepare_ms: int | None = None

        try:
            prepare_start = time.perf_counter()
            primary_attempt = self._attempts.prepare_attempt(
                slot=primary_slot,
                prefix=command.prefix,
                suffix=command.suffix,
                active_file=command.active_file,
            )
            primary_prepare_ms = elapsed_ms(prepare_start)
        except (OSError, PromptTemplateError):
            logger.warning(
                "ai_completion_system_prompt_unavailable",
                template_id=getattr(self._settings, "LLM_COMPLETION_TEMPLATE_ID", None),
            )
            return InlineCompletionResult(
                completion="",
                enabled=False,
                eval_meta=PromptEvalMeta(
                    template_id=default_template_id,
                    outcome="error",
                    system_prompt_chars=0,
                    prefix_chars=len(command.prefix),
                    suffix_chars=len(command.suffix),
                ),
            )

        logger.info(
            "ai_inline_completion_request",
            template_id=primary_attempt.template_id,
            provider_preference=command.inline_completion_provider,
            provider_slot=primary_attempt.slot,
            provider_kind=self._attempts.slot_kind(primary_attempt.slot),
            model=primary_attempt.model,
            remote_allowed=remote_allowed,
            active_file=command.active_file,
            incoming_prefix_len=len(command.prefix),
            incoming_suffix_len=len(command.suffix),
            prefix_len=len(primary_attempt.request.prefix),
            suffix_len=len(primary_attempt.request.suffix),
            system_prompt_tokens=primary_attempt.system_prompt_tokens,
            prefix_tokens=primary_attempt.prefix_tokens,
            suffix_tokens=primary_attempt.suffix_tokens,
            prompt_tokens_total=primary_attempt.prompt_tokens_total,
            prompt_budget_tokens=primary_attempt.prompt_budget_tokens,
            context_window_tokens=self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_COMPLETION_MAX_TOKENS,
            safety_margin_tokens=self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS,
            user_id=str(actor.id),
        )

        response, failure, primary_provider_ms = await try_complete(
            provider=primary_attempt.provider,
            request=primary_attempt.request,
            system_prompt=primary_attempt.system_prompt,
        )

        if failure is not None:
            logger.info(
                "ai_inline_completion_failed",
                template_id=primary_attempt.template_id,
                provider_slot=primary_attempt.slot,
                provider_kind=self._attempts.slot_kind(primary_attempt.slot),
                model=primary_attempt.model,
                active_file=command.active_file,
                prefix_len=len(primary_attempt.request.prefix),
                suffix_len=len(primary_attempt.request.suffix),
                system_prompt_tokens=primary_attempt.system_prompt_tokens,
                prefix_tokens=primary_attempt.prefix_tokens,
                suffix_tokens=primary_attempt.suffix_tokens,
                prompt_tokens_total=primary_attempt.prompt_tokens_total,
                prompt_budget_tokens=primary_attempt.prompt_budget_tokens,
                context_window_tokens=self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS,
                max_output_tokens=self._settings.LLM_COMPLETION_MAX_TOKENS,
                safety_margin_tokens=self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS,
                user_id=str(actor.id),
                outcome=failure.outcome,
                retryable=failure.retryable,
                status_code=failure.status_code,
                prepare_ms=primary_prepare_ms,
                provider_ms=primary_provider_ms,
                total_ms=elapsed_ms(request_start),
            )

            if failure.outcome == "over_budget":
                return InlineCompletionResult(
                    completion="",
                    enabled=True,
                    eval_meta=build_eval_meta(attempt=primary_attempt, outcome="over_budget"),
                )

            if failure.retryable and fallback_slot is not None:
                if self._attempts.slot_is_remote(fallback_slot) and not remote_allowed:
                    if not self._settings.AI_REMOTE_PROVIDERS_ENABLED or should_prompt_for_remote:
                        notice_code, notice_message = self._notice_for_remote_block()
                        return InlineCompletionResult(
                            completion="",
                            enabled=True,
                            notice_message=notice_message,
                            notice_variant="warning",
                            notice_code=notice_code,
                            eval_meta=build_eval_meta(
                                attempt=primary_attempt,
                                outcome="timeout" if failure.outcome == "timeout" else "error",
                            ),
                        )
                else:
                    try:
                        prepare_start = time.perf_counter()
                        fallback_attempt = self._attempts.prepare_attempt(
                            slot=fallback_slot,
                            prefix=command.prefix,
                            suffix=command.suffix,
                            active_file=command.active_file,
                        )
                        fallback_prepare_ms = elapsed_ms(prepare_start)
                    except (OSError, PromptTemplateError):
                        return InlineCompletionResult(
                            completion="",
                            enabled=True,
                            eval_meta=build_eval_meta(
                                attempt=primary_attempt,
                                outcome="timeout" if failure.outcome == "timeout" else "error",
                            ),
                        )

                    logger.info(
                        "ai_inline_completion_retry",
                        template_id=primary_attempt.template_id,
                        from_provider_slot=primary_attempt.slot,
                        to_provider_slot=fallback_attempt.slot,
                        to_provider_kind=self._attempts.slot_kind(fallback_attempt.slot),
                        to_model=fallback_attempt.model,
                        outcome=failure.outcome,
                        active_file=command.active_file,
                        user_id=str(actor.id),
                    )

                    response, failure, fallback_provider_ms = await try_complete(
                        provider=fallback_attempt.provider,
                        request=fallback_attempt.request,
                        system_prompt=fallback_attempt.system_prompt,
                    )

                    if failure is not None:
                        logger.info(
                            "ai_inline_completion_failed",
                            template_id=fallback_attempt.template_id,
                            provider_slot=fallback_attempt.slot,
                            provider_kind=self._attempts.slot_kind(fallback_attempt.slot),
                            model=fallback_attempt.model,
                            active_file=command.active_file,
                            prefix_len=len(fallback_attempt.request.prefix),
                            suffix_len=len(fallback_attempt.request.suffix),
                            user_id=str(actor.id),
                            outcome=failure.outcome,
                            retryable=failure.retryable,
                            status_code=failure.status_code,
                            prepare_ms=fallback_prepare_ms,
                            provider_ms=fallback_provider_ms,
                            total_ms=elapsed_ms(request_start),
                        )

                        if failure.outcome == "over_budget":
                            return InlineCompletionResult(
                                completion="",
                                enabled=True,
                                eval_meta=build_eval_meta(
                                    attempt=fallback_attempt, outcome="over_budget"
                                ),
                            )

                        return InlineCompletionResult(
                            completion="",
                            enabled=True,
                            eval_meta=build_eval_meta(
                                attempt=fallback_attempt,
                                outcome="timeout" if failure.outcome == "timeout" else "error",
                            ),
                        )

                    assert response is not None
                    return await self._finalize_response(
                        attempt=fallback_attempt,
                        response=response,
                        actor=actor,
                        command=command,
                        prepare_ms=fallback_prepare_ms,
                        provider_ms=fallback_provider_ms,
                        request_start=request_start,
                        raw_correlation_id=raw_correlation_id,
                    )

            return InlineCompletionResult(
                completion="",
                enabled=True,
                eval_meta=build_eval_meta(
                    attempt=primary_attempt,
                    outcome="timeout" if failure.outcome == "timeout" else "error",
                ),
            )

        assert response is not None
        return await self._finalize_response(
            attempt=primary_attempt,
            response=response,
            actor=actor,
            command=command,
            prepare_ms=primary_prepare_ms,
            provider_ms=primary_provider_ms,
            request_start=request_start,
            raw_correlation_id=raw_correlation_id,
        )


__all__ = ["InlineCompletionFlow"]
