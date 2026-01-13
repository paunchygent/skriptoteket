from __future__ import annotations

import re
from collections.abc import Callable

import httpx
import structlog

from skriptoteket.application.editor.prompt_budget import apply_inline_completion_budget
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.llm import (
    InlineCompletionCommand,
    InlineCompletionHandlerProtocol,
    InlineCompletionProviderProtocol,
    InlineCompletionResult,
    LLMCompletionRequest,
    PromptEvalMeta,
)
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol

logger = structlog.get_logger(__name__)

_CODE_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)


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


def _normalize_inline_completion(completion: str) -> str:
    if not completion:
        return ""
    fenced = _extract_first_fenced_block(completion)
    if fenced is not None:
        return fenced.strip("\n")
    return completion.strip("\n")


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


class InlineCompletionHandler(InlineCompletionHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        provider: InlineCompletionProviderProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._provider = provider
        self._token_counters = token_counters
        self._system_prompt_loader = system_prompt_loader or (
            lambda template_id: compose_system_prompt(
                template_id=template_id,
                settings=settings,
                token_counter=self._token_counters.for_model(model=settings.LLM_COMPLETION_MODEL),
            ).text
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

        template_id = self._settings.LLM_COMPLETION_TEMPLATE_ID
        token_counter = self._token_counters.for_model(model=self._settings.LLM_COMPLETION_MODEL)
        try:
            system_prompt = self._system_prompt_loader(template_id)
        except (OSError, PromptTemplateError):
            logger.warning(
                "ai_completion_system_prompt_unavailable",
                template_id=getattr(self._settings, "LLM_COMPLETION_TEMPLATE_ID", None),
            )
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

        system_prompt, prefix, suffix = apply_inline_completion_budget(
            system_prompt=system_prompt,
            prefix=command.prefix,
            suffix=command.suffix,
            context_window_tokens=self._settings.LLM_COMPLETION_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_COMPLETION_MAX_TOKENS,
            safety_margin_tokens=self._settings.LLM_COMPLETION_CONTEXT_SAFETY_MARGIN_TOKENS,
            system_prompt_max_tokens=self._settings.LLM_COMPLETION_SYSTEM_PROMPT_MAX_TOKENS,
            prefix_max_tokens=self._settings.LLM_COMPLETION_PREFIX_MAX_TOKENS,
            suffix_max_tokens=self._settings.LLM_COMPLETION_SUFFIX_MAX_TOKENS,
            token_counter=token_counter,
        )
        request = LLMCompletionRequest(prefix=prefix, suffix=suffix)
        logger.info(
            "ai_inline_completion_request",
            template_id=template_id,
            prefix_len=len(request.prefix),
            suffix_len=len(request.suffix),
            user_id=str(actor.id),
        )

        try:
            response = await self._provider.complete_inline(
                request=request,
                system_prompt=system_prompt,
            )
        except httpx.TimeoutException:
            logger.info(
                "ai_inline_completion_failed",
                template_id=template_id,
                prefix_len=len(request.prefix),
                suffix_len=len(request.suffix),
                user_id=str(actor.id),
            )
            return InlineCompletionResult(
                completion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="timeout",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(request.prefix),
                    suffix_chars=len(request.suffix),
                ),
            )
        except httpx.HTTPStatusError as exc:
            if _is_context_window_error(exc):
                logger.info(
                    "ai_inline_completion_over_budget",
                    template_id=template_id,
                    prefix_len=len(request.prefix),
                    suffix_len=len(request.suffix),
                    user_id=str(actor.id),
                )
                return InlineCompletionResult(
                    completion="",
                    enabled=True,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="over_budget",
                        system_prompt_chars=len(system_prompt),
                        prefix_chars=len(request.prefix),
                        suffix_chars=len(request.suffix),
                    ),
                )

            logger.info(
                "ai_inline_completion_failed",
                template_id=template_id,
                prefix_len=len(request.prefix),
                suffix_len=len(request.suffix),
                user_id=str(actor.id),
                status_code=exc.response.status_code if exc.response is not None else None,
            )
            return InlineCompletionResult(
                completion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="error",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(request.prefix),
                    suffix_chars=len(request.suffix),
                ),
            )
        except (httpx.RequestError, ValueError):
            logger.info(
                "ai_inline_completion_failed",
                template_id=template_id,
                prefix_len=len(request.prefix),
                suffix_len=len(request.suffix),
                user_id=str(actor.id),
            )
            return InlineCompletionResult(
                completion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="error",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(request.prefix),
                    suffix_chars=len(request.suffix),
                ),
            )

        if response.finish_reason == "length":
            return InlineCompletionResult(
                completion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="truncated",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(request.prefix),
                    suffix_chars=len(request.suffix),
                ),
            )

        completion = _normalize_inline_completion(response.completion)
        outcome = "ok" if completion else "empty"
        return InlineCompletionResult(
            completion=completion,
            enabled=True,
            eval_meta=PromptEvalMeta(
                template_id=template_id,
                outcome=outcome,
                system_prompt_chars=len(system_prompt),
                prefix_chars=len(request.prefix),
                suffix_chars=len(request.suffix),
            ),
        )
