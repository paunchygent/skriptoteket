"""Attempt planning + provider invocation for inline completions."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import httpx

from skriptoteket.application.editor.prompt_budget import apply_inline_completion_budget
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model
from skriptoteket.protocols.llm import (
    InlineCompletionProviderPreference,
    InlineCompletionProviderProtocol,
    InlineCompletionProvidersProtocol,
    LLMCompletionRequest,
    LLMCompletionResponse,
)
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol

ProviderSlot = Literal["primary", "fallback"]


@dataclass(frozen=True, slots=True)
class AttemptFailure:
    outcome: Literal["timeout", "over_budget", "error"]
    retryable: bool
    status_code: int | None = None


@dataclass(frozen=True, slots=True)
class PreparedAttempt:
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


def elapsed_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))


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


async def try_complete(
    *,
    provider: InlineCompletionProviderProtocol,
    request: LLMCompletionRequest,
    system_prompt: str,
) -> tuple[LLMCompletionResponse | None, AttemptFailure | None, int]:
    start = time.perf_counter()
    try:
        response = await provider.complete_inline(request=request, system_prompt=system_prompt)
    except httpx.TimeoutException:
        return None, AttemptFailure(outcome="timeout", retryable=True), elapsed_ms(start)
    except httpx.HTTPStatusError as exc:
        if _is_context_window_error(exc):
            return None, AttemptFailure(outcome="over_budget", retryable=False), elapsed_ms(start)
        return (
            None,
            AttemptFailure(
                outcome="error",
                retryable=_is_retryable_http_status(exc),
                status_code=exc.response.status_code if exc.response is not None else None,
            ),
            elapsed_ms(start),
        )
    except httpx.RequestError:
        return None, AttemptFailure(outcome="error", retryable=True), elapsed_ms(start)
    except ValueError:
        return None, AttemptFailure(outcome="error", retryable=False), elapsed_ms(start)

    return response, None, elapsed_ms(start)


class InlineCompletionAttemptPlanner:
    def __init__(
        self,
        *,
        settings: Settings,
        providers: InlineCompletionProvidersProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str, str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._providers = providers
        self._token_counters = token_counters
        self._system_prompt_loader = system_prompt_loader

    def prompt_budget_tokens(self) -> int:
        budget = (
            self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS
            - self._settings.LLM_COMPLETION_MAX_TOKENS
            - self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS
        )
        return budget if budget > 0 else 0

    def model_for_slot(self, slot: ProviderSlot) -> str:
        if slot == "primary":
            return self._settings.LLM_COMPLETION_MODEL.strip()
        model = self._settings.LLM_COMPLETION_FALLBACK_MODEL.strip()
        return model or self._settings.LLM_COMPLETION_MODEL.strip()

    def provider_for_slot(self, slot: ProviderSlot) -> InlineCompletionProviderProtocol:
        if slot == "primary":
            return self._providers.primary
        if self._providers.fallback is None:
            raise ValueError("Fallback provider is not configured")
        return self._providers.fallback

    def template_id_for_model(self, model: str) -> str:
        if is_gpt5_family_model(model=model):
            configured = self._settings.LLM_COMPLETION_GPT5_TEMPLATE_ID.strip()
            if configured:
                return configured
        return self._settings.LLM_COMPLETION_TEMPLATE_ID.strip()

    def slot_is_remote(self, slot: ProviderSlot) -> bool:
        if slot == "primary":
            return self._providers.primary_is_remote
        return self._providers.fallback_is_remote

    def slot_kind(self, slot: ProviderSlot) -> InlineCompletionProviderPreference:
        return "external" if self.slot_is_remote(slot) else "local"

    def resolve_provider_slots(self) -> tuple[ProviderSlot | None, ProviderSlot | None]:
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

    def prepare_attempt(
        self,
        *,
        slot: ProviderSlot,
        prefix: str,
        suffix: str,
        active_file: str,
    ) -> PreparedAttempt:
        model = self.model_for_slot(slot)
        token_counter = self._token_counters.for_model(model=model)
        template_id = self.template_id_for_model(model)
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
        provider = self.provider_for_slot(slot)
        return PreparedAttempt(
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
            prompt_budget_tokens=self.prompt_budget_tokens(),
        )


__all__ = [
    "AttemptFailure",
    "InlineCompletionAttemptPlanner",
    "PreparedAttempt",
    "ProviderSlot",
    "PromptTemplateError",
    "elapsed_ms",
    "try_complete",
]
