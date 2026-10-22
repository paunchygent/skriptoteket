"""Attempt planning + provider invocation for inline completions."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from skriptoteket.application.editor.prompt_budget import apply_inline_completion_budget
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.llm_door import AiDailyLimitReached, AiDoorCaller, ai_limit_note
from skriptoteket.protocols.llm import (
    EditorLlmProviderError,
    InlineCompletionProviderProtocol,
    LLMCompletionRequest,
    LLMCompletionResponse,
)
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol


@dataclass(frozen=True, slots=True)
class AttemptFailure:
    outcome: Literal["timeout", "over_budget", "error"]
    status_code: int | None = None


@dataclass(frozen=True, slots=True)
class PreparedAttempt:
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


def classify_provider_error(error: EditorLlmProviderError) -> AttemptFailure:
    """Map the door provider's failure kind to the completion outcome."""

    match error.kind:
        case "timeout":
            return AttemptFailure(outcome="timeout")
        case "context_window_exceeded":
            return AttemptFailure(outcome="over_budget")
        case _:
            return AttemptFailure(outcome="error", status_code=error.status_code)


async def try_complete(
    *,
    provider: InlineCompletionProviderProtocol,
    request: LLMCompletionRequest,
    system_prompt: str,
    caller: AiDoorCaller,
) -> tuple[LLMCompletionResponse | None, AttemptFailure | None, int]:
    """Make the one door call; a daily-limit refusal becomes the 429 limit error."""

    start = time.perf_counter()
    try:
        response = await provider.complete_inline(
            request=request, system_prompt=system_prompt, caller=caller
        )
    except AiDailyLimitReached as error:
        raise DomainError(
            code=ErrorCode.AI_DAILY_LIMIT_REACHED,
            message=ai_limit_note(error.limit),
            details={"limit": error.limit.value},
        ) from error
    except EditorLlmProviderError as error:
        return None, classify_provider_error(error), elapsed_ms(start)

    return response, None, elapsed_ms(start)


class InlineCompletionAttemptPlanner:
    def __init__(
        self,
        *,
        settings: Settings,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str, str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._token_counters = token_counters
        self._system_prompt_loader = system_prompt_loader

    def prompt_budget_tokens(self) -> int:
        budget = (
            self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS
            - self._settings.LLM_COMPLETION_MAX_TOKENS
            - self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS
        )
        return budget if budget > 0 else 0

    def model(self) -> str:
        return self._settings.LLM_COMPLETION_MODEL.strip()

    def template_id(self) -> str:
        return self._settings.LLM_COMPLETION_TEMPLATE_ID.strip()

    def prepare_attempt(
        self,
        *,
        prefix: str,
        suffix: str,
        active_file: str,
    ) -> PreparedAttempt:
        model = self.model()
        token_counter = self._token_counters.for_model(model=model)
        template_id = self.template_id()
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
        return PreparedAttempt(
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
    "PromptTemplateError",
    "elapsed_ms",
    "classify_provider_error",
    "try_complete",
]
