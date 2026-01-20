from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import httpx
import structlog
from structlog.contextvars import get_contextvars

from skriptoteket.application.editor.edit_ops.capture import resolve_capture_id
from skriptoteket.application.editor.prompt_budget import apply_inline_completion_budget
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.application.editor.remote_fallback import RemoteFallbackConsent
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    InlineCompletionHandlerProtocol,
    InlineCompletionProviderPreference,
    InlineCompletionProviderProtocol,
    InlineCompletionProvidersProtocol,
    InlineCompletionResult,
    LLMCompletionRequest,
    LLMCompletionResponse,
    PromptEvalMeta,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol

logger = structlog.get_logger(__name__)

_CODE_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)
_QUOTE_CHARS = ("'", '"')

ProviderSlot = Literal["primary", "fallback"]
DropReason = Literal[
    "empty_input",
    "empty_after_cleanup",
    "cursor_overlap_wiped_all",
    "contiguous_echo",
    "dedup_wiped_all",
]

_CAPTURE_PREFIX_TAIL_CHARS = 2_000
_CAPTURE_SUFFIX_HEAD_CHARS = 2_000

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


def _looks_like_fence_tag(line: str) -> bool:
    tag = line.strip()
    if not tag:
        return False
    if len(tag) > 32:
        return False
    return all(ch.isalnum() or ch in ("-", "_", "+", ".") for ch in tag)


def _extract_first_fenced_block(text: str) -> str | None:
    match = _CODE_FENCE_PATTERN.search(text)
    if not match:
        if "```" not in text:
            return None
        parts = text.split("```", 2)
        if len(parts) < 2:
            return None
        content = parts[1]
    else:
        content = match.group(1)

    if "\n" in content:
        first_line, rest = content.split("\n", 1)
        if _looks_like_fence_tag(first_line):
            content = rest
    return content


def _strip_surrounding_quotes(text: str) -> str:
    stripped = text.strip()
    if len(stripped) < 2:
        return text
    if stripped[0] == stripped[-1] and stripped[0] in _QUOTE_CHARS:
        try:
            loaded = json.loads(stripped)
            return loaded if isinstance(loaded, str) else stripped[1:-1]
        except json.JSONDecodeError:
            return stripped[1:-1]
    return text


@dataclass(frozen=True, slots=True)
class _NormalizedInlineCompletion:
    completion: str
    prefix_overlap_chars: int = 0
    suffix_overlap_chars: int = 0
    drop_reason: DropReason | None = None


def _choose_sentinel(*parts: str) -> str:
    for codepoint in range(1, 32):
        sentinel = chr(codepoint)
        if all(sentinel not in part for part in parts):
            return sentinel
    return "\x00"


def _longest_suffix_prefix_overlap(prefix: str, completion: str) -> int:
    if not prefix or not completion:
        return 0
    max_len = min(len(prefix), len(completion))
    if max_len <= 0:
        return 0
    pattern = completion[:max_len]
    tail = prefix[-max_len:]
    sentinel = _choose_sentinel(pattern, tail)
    combined = f"{pattern}{sentinel}{tail}"
    pi = [0] * len(combined)
    for idx in range(1, len(combined)):
        j = pi[idx - 1]
        while j > 0 and combined[idx] != combined[j]:
            j = pi[j - 1]
        if combined[idx] == combined[j]:
            j += 1
        pi[idx] = j
    return pi[-1]


def _strip_prefix_overlap(prefix: str, completion: str) -> tuple[str, int]:
    removed = 0
    while completion:
        overlap = _longest_suffix_prefix_overlap(prefix, completion)
        if overlap <= 0:
            break
        if overlap == 1 and len(completion) == 1:
            break
        completion = completion[overlap:]
        removed += overlap
    return completion, removed


def _strip_suffix_overlap(completion: str, suffix: str) -> tuple[str, int]:
    removed = 0
    while completion:
        overlap = _longest_suffix_prefix_overlap(completion, suffix)
        if overlap <= 0:
            break
        completion = completion[:-overlap]
        removed += overlap
    return completion, removed


def _strip_cursor_overlaps(
    *, completion: str, prefix: str, suffix: str
) -> _NormalizedInlineCompletion:
    if not completion:
        return _NormalizedInlineCompletion(completion="")
    stripped, prefix_removed = _strip_prefix_overlap(prefix, completion)
    stripped, suffix_removed = _strip_suffix_overlap(stripped, suffix)
    return _NormalizedInlineCompletion(
        completion=stripped,
        prefix_overlap_chars=prefix_removed,
        suffix_overlap_chars=suffix_removed,
    )


def _elapsed_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))


def _has_contiguous_echo(prefix: str, suffix: str, completion: str) -> bool:
    completion_lines = [line for line in completion.splitlines() if line.strip()]
    if len(completion_lines) < 2:
        return False
    for idx in range(len(completion_lines) - 1):
        chunk = "\n".join(completion_lines[idx : idx + 2])
        if chunk in prefix or chunk in suffix:
            return True
    return False


def _strip_duplicate_lines(prefix: str, suffix: str, completion: str) -> str:
    prefix_lines = {line.strip() for line in prefix.splitlines() if line.strip()}
    suffix_lines = {line.strip() for line in suffix.splitlines() if line.strip()}
    cleaned_lines: list[str] = []
    for line in completion.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        non_ws_len = len(re.sub(r"\s+", "", line))
        if non_ws_len >= 12 and (stripped in prefix_lines or stripped in suffix_lines):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip("\n")


def _normalize_inline_completion(
    *, completion: str, prefix: str, suffix: str
) -> _NormalizedInlineCompletion:
    if not completion:
        return _NormalizedInlineCompletion(completion="", drop_reason="empty_input")
    fenced = _extract_first_fenced_block(completion)
    if fenced is not None:
        completion = fenced
    completion = _strip_surrounding_quotes(completion)
    completion = completion.strip("\n")
    if not completion:
        return _NormalizedInlineCompletion(completion="", drop_reason="empty_after_cleanup")

    overlap_result = _strip_cursor_overlaps(
        completion=completion,
        prefix=prefix,
        suffix=suffix,
    )
    completion = overlap_result.completion.strip("\n")
    if not completion:
        return _NormalizedInlineCompletion(
            completion="",
            prefix_overlap_chars=overlap_result.prefix_overlap_chars,
            suffix_overlap_chars=overlap_result.suffix_overlap_chars,
            drop_reason="cursor_overlap_wiped_all",
        )
    if _has_contiguous_echo(prefix, suffix, completion):
        return _NormalizedInlineCompletion(
            completion="",
            prefix_overlap_chars=overlap_result.prefix_overlap_chars,
            suffix_overlap_chars=overlap_result.suffix_overlap_chars,
            drop_reason="contiguous_echo",
        )
    completion = _strip_duplicate_lines(prefix, suffix, completion)
    completion = completion.strip("\n")
    if not completion:
        return _NormalizedInlineCompletion(
            completion="",
            prefix_overlap_chars=overlap_result.prefix_overlap_chars,
            suffix_overlap_chars=overlap_result.suffix_overlap_chars,
            drop_reason="dedup_wiped_all",
        )
    return _NormalizedInlineCompletion(
        completion=completion,
        prefix_overlap_chars=overlap_result.prefix_overlap_chars,
        suffix_overlap_chars=overlap_result.suffix_overlap_chars,
    )


def _is_context_window_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None:
        return False
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except ValueError:
        payload = None
    haystack = str(payload) if payload is not None else response.text
    return "exceed_context_size_error" in haystack.lower()


def _is_retryable_http_status(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None:
        return False
    return response.status_code == 429 or 500 <= response.status_code <= 599


@dataclass(frozen=True, slots=True)
class _AttemptFailure:
    outcome: Literal["timeout", "over_budget", "error"]
    retryable: bool
    status_code: int | None = None


@dataclass(frozen=True, slots=True)
class _PreparedAttempt:
    slot: ProviderSlot
    provider: InlineCompletionProviderProtocol
    model: str
    template_id: str
    system_prompt: str
    request: LLMCompletionRequest
    system_prompt_tokens: int
    prefix_tokens: int
    suffix_tokens: int
    prompt_tokens_total: int
    prompt_budget_tokens: int


class InlineCompletionHandler(InlineCompletionHandlerProtocol):
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
        self._token_counters = token_counters
        self._system_prompt_loader = system_prompt_loader

    def _prompt_budget_tokens(self) -> int:
        budget = (
            self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS
            - self._settings.LLM_COMPLETION_MAX_TOKENS
            - self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS
        )
        return budget if budget > 0 else 0

    def _model_for_slot(self, slot: ProviderSlot) -> str:
        if slot == "primary":
            return self._settings.LLM_COMPLETION_MODEL.strip()
        model = self._settings.LLM_COMPLETION_FALLBACK_MODEL.strip()
        return model or self._settings.LLM_COMPLETION_MODEL.strip()

    def _provider_for_slot(self, slot: ProviderSlot) -> InlineCompletionProviderProtocol:
        if slot == "primary":
            return self._providers.primary
        if self._providers.fallback is None:
            raise ValueError("Fallback provider is not configured")
        return self._providers.fallback

    def _template_id_for_model(self, model: str) -> str:
        if is_gpt5_family_model(model=model):
            configured = self._settings.LLM_COMPLETION_GPT5_TEMPLATE_ID.strip()
            if configured:
                return configured
        return self._settings.LLM_COMPLETION_TEMPLATE_ID.strip()

    def _slot_is_remote(self, slot: ProviderSlot) -> bool:
        if slot == "primary":
            return self._providers.primary_is_remote
        return self._providers.fallback_is_remote

    def _slot_kind(self, slot: ProviderSlot) -> InlineCompletionProviderPreference:
        return "external" if self._slot_is_remote(slot) else "local"

    def _resolve_provider_slots(self) -> tuple[ProviderSlot | None, ProviderSlot | None]:
        """Return (local_slot, external_slot) if available."""

        local_slot: ProviderSlot | None = None
        external_slot: ProviderSlot | None = None

        if self._providers.primary_is_remote:
            external_slot = "primary"
        else:
            local_slot = "primary"

        if self._providers.fallback is not None:
            if self._providers.fallback_is_remote and external_slot is None:
                external_slot = "fallback"
            elif not self._providers.fallback_is_remote and local_slot is None:
                local_slot = "fallback"

        return local_slot, external_slot

    def _notice_for_remote_block(self) -> tuple[str, str]:
        if not self._settings.AI_REMOTE_PROVIDERS_ENABLED:
            return REMOTE_PROVIDERS_DISABLED_NOTICE_CODE, REMOTE_PROVIDERS_DISABLED_NOTICE_MESSAGE
        return REMOTE_FALLBACK_REQUIRED_NOTICE_CODE, REMOTE_FALLBACK_REQUIRED_NOTICE_MESSAGE

    def _prepare_attempt(
        self,
        *,
        slot: ProviderSlot,
        prefix: str,
        suffix: str,
        active_file: str,
    ) -> _PreparedAttempt:
        model = self._model_for_slot(slot)
        token_counter = self._token_counters.for_model(model=model)
        template_id = self._template_id_for_model(model)
        if self._system_prompt_loader is not None:
            system_prompt = self._system_prompt_loader(template_id, model)
        else:
            system_prompt = compose_system_prompt(
                template_id=template_id,
                settings=self._settings,
                token_counter=token_counter,
            ).text

        system_prompt, budgeted_prefix, budgeted_suffix = apply_inline_completion_budget(
            system_prompt=system_prompt,
            prefix=prefix,
            suffix=suffix,
            context_window_tokens=self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_COMPLETION_MAX_TOKENS,
            safety_margin_tokens=self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS,
            system_prompt_max_tokens=self._settings.LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS,
            prefix_max_tokens=self._settings.LLM_COMPLETION_PREFIX_MAX_TOKENS,
            suffix_max_tokens=self._settings.LLM_COMPLETION_SUFFIX_MAX_TOKENS,
            token_counter=token_counter,
        )
        system_prompt_tokens = token_counter.count_system_prompt(content=system_prompt)
        prefix_tokens = token_counter.count_text(budgeted_prefix)
        suffix_tokens = token_counter.count_text(budgeted_suffix)
        prompt_tokens_total = system_prompt_tokens + prefix_tokens + suffix_tokens
        request = LLMCompletionRequest(
            prefix=budgeted_prefix,
            suffix=budgeted_suffix,
            active_file=active_file,
        )
        provider = self._provider_for_slot(slot)
        return _PreparedAttempt(
            slot=slot,
            provider=provider,
            model=model,
            template_id=template_id,
            system_prompt=system_prompt,
            request=request,
            system_prompt_tokens=system_prompt_tokens,
            prefix_tokens=prefix_tokens,
            suffix_tokens=suffix_tokens,
            prompt_tokens_total=prompt_tokens_total,
            prompt_budget_tokens=self._prompt_budget_tokens(),
        )

    def _log_normalized(
        self,
        *,
        attempt: _PreparedAttempt,
        raw_completion: str,
        normalized_completion: str,
        prefix_overlap_chars: int = 0,
        suffix_overlap_chars: int = 0,
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
            provider_kind=self._slot_kind(attempt.slot),
            model=attempt.model,
            raw_chars=len(raw_completion),
            normalized_chars=len(normalized_completion),
            prefix_overlap_chars=prefix_overlap_chars,
            suffix_overlap_chars=suffix_overlap_chars,
            dropped=bool(raw_completion) and not normalized_completion,
            drop_reason=drop_reason,
            prepare_ms=prepare_ms,
            provider_ms=provider_ms,
            normalize_ms=normalize_ms,
            total_ms=total_ms,
            user_id=user_id,
        )

    def _log_truncated(
        self,
        *,
        attempt: _PreparedAttempt,
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
            provider_kind=self._slot_kind(attempt.slot),
            model=attempt.model,
            finish_reason=finish_reason,
            raw_chars=len(raw_completion),
            prepare_ms=prepare_ms,
            provider_ms=provider_ms,
            total_ms=total_ms,
            user_id=user_id,
        )

    async def _capture_completion(
        self,
        *,
        capture_id: object,
        attempt: _PreparedAttempt,
        actor: User,
        command: InlineCompletionCommand,
        finish_reason: str | None,
        raw_completion: str,
        normalized: _NormalizedInlineCompletion,
        prepare_ms: int | None,
        provider_ms: int | None,
        normalize_ms: int | None,
        total_ms: int | None,
    ) -> None:
        if self._settings.ENVIRONMENT == "production":
            return
        if not self._settings.LLM_CAPTURE_ON_SUCCESS_ENABLED:
            return
        if actor.role not in {Role.ADMIN, Role.SUPERUSER}:
            return
        capture_uuid = resolve_capture_id(raw_correlation_id=capture_id)
        if capture_uuid is None:
            return

        prefix = attempt.request.prefix
        suffix = attempt.request.suffix
        prefix_tail = prefix[-_CAPTURE_PREFIX_TAIL_CHARS:]
        suffix_head = suffix[:_CAPTURE_SUFFIX_HEAD_CHARS]
        preview_prefix = prefix_tail[-200:]
        preview_suffix = suffix_head[:200]

        await self._capture_store.write_capture(
            kind="inline_completion_response",
            capture_id=capture_uuid,
            payload={
                "template_id": attempt.template_id,
                "provider_slot": attempt.slot,
                "provider_kind": self._slot_kind(attempt.slot),
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
                "context_window_tokens": self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS,
                "max_output_tokens": self._settings.LLM_COMPLETION_MAX_TOKENS,
                "safety_margin_tokens": self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS,
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
                "raw_chars": len(raw_completion),
                "normalized_chars": len(normalized.completion),
                "prepare_ms": prepare_ms,
                "provider_ms": provider_ms,
                "normalize_ms": normalize_ms,
                "total_ms": total_ms,
                "user_id": str(actor.id),
            },
        )

    async def _try_complete(
        self,
        *,
        provider: InlineCompletionProviderProtocol,
        request: LLMCompletionRequest,
        system_prompt: str,
    ) -> tuple[LLMCompletionResponse | None, _AttemptFailure | None, int]:
        start = time.perf_counter()
        try:
            response = await provider.complete_inline(request=request, system_prompt=system_prompt)
        except httpx.TimeoutException:
            return None, _AttemptFailure(outcome="timeout", retryable=True), _elapsed_ms(start)
        except httpx.HTTPStatusError as exc:
            if _is_context_window_error(exc):
                return (
                    None,
                    _AttemptFailure(outcome="over_budget", retryable=False),
                    _elapsed_ms(start),
                )
            return (
                None,
                _AttemptFailure(
                    outcome="error",
                    retryable=_is_retryable_http_status(exc),
                    status_code=exc.response.status_code if exc.response is not None else None,
                ),
                _elapsed_ms(start),
            )
        except httpx.RequestError:
            return None, _AttemptFailure(outcome="error", retryable=True), _elapsed_ms(start)
        except ValueError:
            return None, _AttemptFailure(outcome="error", retryable=False), _elapsed_ms(start)

        return response, None, _elapsed_ms(start)

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
        local_slot, external_slot = self._resolve_provider_slots()

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
            # We have providers configured, but none are allowed
            # (e.g. remote-only and remote is blocked).
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

        def build_eval_meta(
            *,
            attempt: _PreparedAttempt,
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
                prefix_chars=len(attempt.request.prefix),
                suffix_chars=len(attempt.request.suffix),
                raw_chars=raw_chars,
                normalized_chars=normalized_chars,
                prefix_overlap_chars=prefix_overlap_chars,
                suffix_overlap_chars=suffix_overlap_chars,
                prepare_ms=prepare_ms,
                provider_ms=provider_ms,
                normalize_ms=normalize_ms,
                total_ms=total_ms,
            )

        try:
            prepare_start = time.perf_counter()
            primary_attempt = self._prepare_attempt(
                slot=primary_slot,
                prefix=command.prefix,
                suffix=command.suffix,
                active_file=command.active_file,
            )
            primary_prepare_ms = _elapsed_ms(prepare_start)
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
            provider_kind=self._slot_kind(primary_attempt.slot),
            model=primary_attempt.model,
            remote_allowed=remote_allowed,
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
        )

        response, failure, primary_provider_ms = await self._try_complete(
            provider=primary_attempt.provider,
            request=primary_attempt.request,
            system_prompt=primary_attempt.system_prompt,
        )

        if failure is not None:
            logger.info(
                "ai_inline_completion_failed",
                template_id=primary_attempt.template_id,
                provider_slot=primary_attempt.slot,
                provider_kind=self._slot_kind(primary_attempt.slot),
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
                total_ms=_elapsed_ms(request_start),
            )

            if failure.outcome == "over_budget":
                return InlineCompletionResult(
                    completion="",
                    enabled=True,
                    eval_meta=build_eval_meta(attempt=primary_attempt, outcome="over_budget"),
                )

            if failure.retryable and fallback_slot is not None:
                if self._slot_is_remote(fallback_slot) and not remote_allowed:
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
                        fallback_attempt = self._prepare_attempt(
                            slot=fallback_slot,
                            prefix=command.prefix,
                            suffix=command.suffix,
                            active_file=command.active_file,
                        )
                        fallback_prepare_ms = _elapsed_ms(prepare_start)
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
                        to_provider_kind=self._slot_kind(fallback_attempt.slot),
                        to_model=fallback_attempt.model,
                        outcome=failure.outcome,
                        active_file=command.active_file,
                        user_id=str(actor.id),
                    )

                    response, failure, fallback_provider_ms = await self._try_complete(
                        provider=fallback_attempt.provider,
                        request=fallback_attempt.request,
                        system_prompt=fallback_attempt.system_prompt,
                    )

                    if failure is not None:
                        logger.info(
                            "ai_inline_completion_failed",
                            template_id=fallback_attempt.template_id,
                            provider_slot=fallback_attempt.slot,
                            provider_kind=self._slot_kind(fallback_attempt.slot),
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
                            total_ms=_elapsed_ms(request_start),
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
                    if response.finish_reason in ("length", "incomplete"):
                        raw_completion = response.completion or ""
                        truncated_total_ms = _elapsed_ms(request_start)
                        self._log_truncated(
                            attempt=fallback_attempt,
                            finish_reason=response.finish_reason,
                            raw_completion=raw_completion,
                            prepare_ms=fallback_prepare_ms,
                            provider_ms=fallback_provider_ms,
                            total_ms=truncated_total_ms,
                            user_id=str(actor.id),
                        )
                        normalize_start = time.perf_counter()
                        normalized = _normalize_inline_completion(
                            completion=raw_completion,
                            prefix=fallback_attempt.request.prefix,
                            suffix=fallback_attempt.request.suffix,
                        )
                        normalize_ms = _elapsed_ms(normalize_start)
                        completion = normalized.completion
                        total_ms = _elapsed_ms(request_start)
                        self._log_normalized(
                            attempt=fallback_attempt,
                            raw_completion=raw_completion,
                            normalized_completion=completion,
                            prefix_overlap_chars=normalized.prefix_overlap_chars,
                            suffix_overlap_chars=normalized.suffix_overlap_chars,
                            drop_reason=normalized.drop_reason,
                            prepare_ms=fallback_prepare_ms,
                            provider_ms=fallback_provider_ms,
                            normalize_ms=normalize_ms,
                            total_ms=total_ms,
                            user_id=str(actor.id),
                        )
                        await self._capture_completion(
                            capture_id=raw_correlation_id,
                            attempt=fallback_attempt,
                            actor=actor,
                            command=command,
                            finish_reason=response.finish_reason,
                            raw_completion=raw_completion,
                            normalized=normalized,
                            prepare_ms=fallback_prepare_ms,
                            provider_ms=fallback_provider_ms,
                            normalize_ms=normalize_ms,
                            total_ms=total_ms,
                        )
                        return InlineCompletionResult(
                            completion=completion,
                            enabled=True,
                            eval_meta=build_eval_meta(
                                attempt=fallback_attempt,
                                outcome="truncated",
                                raw_chars=len(raw_completion),
                                normalized_chars=len(completion),
                                prefix_overlap_chars=normalized.prefix_overlap_chars,
                                suffix_overlap_chars=normalized.suffix_overlap_chars,
                                prepare_ms=fallback_prepare_ms,
                                provider_ms=fallback_provider_ms,
                                normalize_ms=normalize_ms,
                                total_ms=total_ms,
                            ),
                        )

                    raw_completion = response.completion
                    normalize_start = time.perf_counter()
                    normalized = _normalize_inline_completion(
                        completion=raw_completion,
                        prefix=fallback_attempt.request.prefix,
                        suffix=fallback_attempt.request.suffix,
                    )
                    normalize_ms = _elapsed_ms(normalize_start)
                    completion = normalized.completion
                    total_ms = _elapsed_ms(request_start)
                    self._log_normalized(
                        attempt=fallback_attempt,
                        raw_completion=raw_completion,
                        normalized_completion=completion,
                        prefix_overlap_chars=normalized.prefix_overlap_chars,
                        suffix_overlap_chars=normalized.suffix_overlap_chars,
                        drop_reason=normalized.drop_reason,
                        prepare_ms=fallback_prepare_ms,
                        provider_ms=fallback_provider_ms,
                        normalize_ms=normalize_ms,
                        total_ms=total_ms,
                        user_id=str(actor.id),
                    )
                    await self._capture_completion(
                        capture_id=raw_correlation_id,
                        attempt=fallback_attempt,
                        actor=actor,
                        command=command,
                        finish_reason=response.finish_reason,
                        raw_completion=raw_completion,
                        normalized=normalized,
                        prepare_ms=fallback_prepare_ms,
                        provider_ms=fallback_provider_ms,
                        normalize_ms=normalize_ms,
                        total_ms=total_ms,
                    )
                    outcome = "ok" if completion else "empty"
                    return InlineCompletionResult(
                        completion=completion,
                        enabled=True,
                        eval_meta=build_eval_meta(
                            attempt=fallback_attempt,
                            outcome=outcome,
                            raw_chars=len(raw_completion),
                            normalized_chars=len(completion),
                            prefix_overlap_chars=normalized.prefix_overlap_chars,
                            suffix_overlap_chars=normalized.suffix_overlap_chars,
                            prepare_ms=fallback_prepare_ms,
                            provider_ms=fallback_provider_ms,
                            normalize_ms=normalize_ms,
                            total_ms=total_ms,
                        ),
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
        if response.finish_reason in ("length", "incomplete"):
            raw_completion = response.completion or ""
            truncated_total_ms = _elapsed_ms(request_start)
            self._log_truncated(
                attempt=primary_attempt,
                finish_reason=response.finish_reason,
                raw_completion=raw_completion,
                prepare_ms=primary_prepare_ms,
                provider_ms=primary_provider_ms,
                total_ms=truncated_total_ms,
                user_id=str(actor.id),
            )
            normalize_start = time.perf_counter()
            normalized = _normalize_inline_completion(
                completion=raw_completion,
                prefix=primary_attempt.request.prefix,
                suffix=primary_attempt.request.suffix,
            )
            normalize_ms = _elapsed_ms(normalize_start)
            completion = normalized.completion
            total_ms = _elapsed_ms(request_start)
            self._log_normalized(
                attempt=primary_attempt,
                raw_completion=raw_completion,
                normalized_completion=completion,
                prefix_overlap_chars=normalized.prefix_overlap_chars,
                suffix_overlap_chars=normalized.suffix_overlap_chars,
                drop_reason=normalized.drop_reason,
                prepare_ms=primary_prepare_ms,
                provider_ms=primary_provider_ms,
                normalize_ms=normalize_ms,
                total_ms=total_ms,
                user_id=str(actor.id),
            )
            await self._capture_completion(
                capture_id=raw_correlation_id,
                attempt=primary_attempt,
                actor=actor,
                command=command,
                finish_reason=response.finish_reason,
                raw_completion=raw_completion,
                normalized=normalized,
                prepare_ms=primary_prepare_ms,
                provider_ms=primary_provider_ms,
                normalize_ms=normalize_ms,
                total_ms=total_ms,
            )
            return InlineCompletionResult(
                completion=completion,
                enabled=True,
                eval_meta=build_eval_meta(
                    attempt=primary_attempt,
                    outcome="truncated",
                    raw_chars=len(raw_completion),
                    normalized_chars=len(completion),
                    prefix_overlap_chars=normalized.prefix_overlap_chars,
                    suffix_overlap_chars=normalized.suffix_overlap_chars,
                    prepare_ms=primary_prepare_ms,
                    provider_ms=primary_provider_ms,
                    normalize_ms=normalize_ms,
                    total_ms=total_ms,
                ),
            )

        raw_completion = response.completion
        normalize_start = time.perf_counter()
        normalized = _normalize_inline_completion(
            completion=raw_completion,
            prefix=primary_attempt.request.prefix,
            suffix=primary_attempt.request.suffix,
        )
        normalize_ms = _elapsed_ms(normalize_start)
        completion = normalized.completion
        total_ms = _elapsed_ms(request_start)
        self._log_normalized(
            attempt=primary_attempt,
            raw_completion=raw_completion,
            normalized_completion=completion,
            prefix_overlap_chars=normalized.prefix_overlap_chars,
            suffix_overlap_chars=normalized.suffix_overlap_chars,
            drop_reason=normalized.drop_reason,
            prepare_ms=primary_prepare_ms,
            provider_ms=primary_provider_ms,
            normalize_ms=normalize_ms,
            total_ms=total_ms,
            user_id=str(actor.id),
        )
        await self._capture_completion(
            capture_id=raw_correlation_id,
            attempt=primary_attempt,
            actor=actor,
            command=command,
            finish_reason=response.finish_reason,
            raw_completion=raw_completion,
            normalized=normalized,
            prepare_ms=primary_prepare_ms,
            provider_ms=primary_provider_ms,
            normalize_ms=normalize_ms,
            total_ms=total_ms,
        )
        outcome = "ok" if completion else "empty"
        return InlineCompletionResult(
            completion=completion,
            enabled=True,
            eval_meta=build_eval_meta(
                attempt=primary_attempt,
                outcome=outcome,
                raw_chars=len(raw_completion),
                normalized_chars=len(completion),
                prefix_overlap_chars=normalized.prefix_overlap_chars,
                suffix_overlap_chars=normalized.suffix_overlap_chars,
                prepare_ms=primary_prepare_ms,
                provider_ms=primary_provider_ms,
                normalize_ms=normalize_ms,
                total_ms=total_ms,
            ),
        )
