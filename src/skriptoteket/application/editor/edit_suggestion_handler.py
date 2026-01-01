from __future__ import annotations

import re
from collections.abc import Callable

import httpx
import structlog

from skriptoteket.application.editor.prompt_budget import apply_edit_suggestion_budget
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.llm import (
    EditSuggestionCommand,
    EditSuggestionHandlerProtocol,
    EditSuggestionProviderProtocol,
    EditSuggestionResult,
    LLMEditRequest,
    PromptEvalMeta,
)

logger = structlog.get_logger(__name__)

_CODE_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n(.*?)```", re.DOTALL)


def _default_instruction(instruction: str | None) -> str:
    if instruction is None:
        return "Förbättra den markerade koden."
    trimmed = instruction.strip()
    return trimmed if trimmed else "Förbättra den markerade koden."


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


def _normalize_edit_suggestion(suggestion: str) -> str:
    if not suggestion:
        return ""
    fenced = _extract_first_fenced_block(suggestion)
    if fenced is not None:
        return fenced.strip("\n")
    return suggestion.strip("\n")


class EditSuggestionHandler(EditSuggestionHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        provider: EditSuggestionProviderProtocol,
        system_prompt_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._provider = provider
        self._system_prompt_loader = system_prompt_loader or (
            lambda template_id: compose_system_prompt(
                template_id=template_id, settings=settings
            ).text
        )

    async def handle(
        self,
        *,
        actor: User,
        command: EditSuggestionCommand,
    ) -> EditSuggestionResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        if not self._settings.LLM_EDIT_ENABLED:
            return EditSuggestionResult(
                suggestion="",
                enabled=False,
                eval_meta=PromptEvalMeta(
                    template_id=self._settings.LLM_EDIT_TEMPLATE_ID,
                    outcome="error",
                    system_prompt_chars=0,
                    prefix_chars=len(command.prefix),
                    selection_chars=len(command.selection),
                    suffix_chars=len(command.suffix),
                    instruction_chars=len(command.instruction or ""),
                ),
            )

        if not command.selection.strip():
            return EditSuggestionResult(
                suggestion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=self._settings.LLM_EDIT_TEMPLATE_ID,
                    outcome="error",
                    system_prompt_chars=0,
                    prefix_chars=len(command.prefix),
                    selection_chars=len(command.selection),
                    suffix_chars=len(command.suffix),
                    instruction_chars=len(command.instruction or ""),
                ),
            )

        template_id = self._settings.LLM_EDIT_TEMPLATE_ID
        try:
            system_prompt = self._system_prompt_loader(template_id)
        except (OSError, PromptTemplateError):
            logger.warning(
                "ai_edit_system_prompt_unavailable",
                template_id=getattr(self._settings, "LLM_EDIT_TEMPLATE_ID", None),
            )
            return EditSuggestionResult(
                suggestion="",
                enabled=False,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="error",
                    system_prompt_chars=0,
                    prefix_chars=len(command.prefix),
                    selection_chars=len(command.selection),
                    suffix_chars=len(command.suffix),
                    instruction_chars=len(command.instruction or ""),
                ),
            )

        instruction = _default_instruction(command.instruction)

        system_prompt, instruction, prefix, selection, suffix = apply_edit_suggestion_budget(
            system_prompt=system_prompt,
            instruction=instruction,
            prefix=command.prefix,
            selection=command.selection,
            suffix=command.suffix,
            context_window_tokens=self._settings.LLM_EDIT_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_EDIT_MAX_TOKENS,
            safety_margin_tokens=self._settings.LLM_EDIT_CONTEXT_SAFETY_MARGIN_TOKENS,
            system_prompt_max_tokens=self._settings.LLM_EDIT_SYSTEM_PROMPT_MAX_TOKENS,
            instruction_max_tokens=self._settings.LLM_EDIT_INSTRUCTION_MAX_TOKENS,
            selection_max_tokens=self._settings.LLM_EDIT_SELECTION_MAX_TOKENS,
            prefix_max_tokens=self._settings.LLM_EDIT_PREFIX_MAX_TOKENS,
            suffix_max_tokens=self._settings.LLM_EDIT_SUFFIX_MAX_TOKENS,
        )

        if not selection.strip():
            return EditSuggestionResult(
                suggestion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="over_budget",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(prefix),
                    selection_chars=len(selection),
                    suffix_chars=len(suffix),
                    instruction_chars=len(instruction),
                ),
            )

        request = LLMEditRequest(
            prefix=prefix,
            selection=selection,
            suffix=suffix,
            instruction=instruction,
        )
        logger.info(
            "ai_edit_suggestion_request",
            template_id=template_id,
            prefix_len=len(request.prefix),
            selection_len=len(request.selection),
            suffix_len=len(request.suffix),
            user_id=str(actor.id),
        )

        try:
            response = await self._provider.suggest_edits(
                request=request,
                system_prompt=system_prompt,
            )
        except httpx.TimeoutException:
            logger.info(
                "ai_edit_suggestion_failed",
                template_id=template_id,
                prefix_len=len(request.prefix),
                selection_len=len(request.selection),
                suffix_len=len(request.suffix),
                user_id=str(actor.id),
            )
            return EditSuggestionResult(
                suggestion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="timeout",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(request.prefix),
                    selection_chars=len(request.selection),
                    suffix_chars=len(request.suffix),
                    instruction_chars=len(instruction),
                ),
            )
        except httpx.HTTPStatusError as exc:
            if _is_context_window_error(exc):
                logger.info(
                    "ai_edit_suggestion_over_budget",
                    template_id=template_id,
                    prefix_len=len(request.prefix),
                    selection_len=len(request.selection),
                    suffix_len=len(request.suffix),
                    user_id=str(actor.id),
                )
                return EditSuggestionResult(
                    suggestion="",
                    enabled=True,
                    eval_meta=PromptEvalMeta(
                        template_id=template_id,
                        outcome="over_budget",
                        system_prompt_chars=len(system_prompt),
                        prefix_chars=len(request.prefix),
                        selection_chars=len(request.selection),
                        suffix_chars=len(request.suffix),
                        instruction_chars=len(instruction),
                    ),
                )

            logger.info(
                "ai_edit_suggestion_failed",
                template_id=template_id,
                prefix_len=len(request.prefix),
                selection_len=len(request.selection),
                suffix_len=len(request.suffix),
                user_id=str(actor.id),
                status_code=exc.response.status_code if exc.response is not None else None,
            )
            return EditSuggestionResult(
                suggestion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="error",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(request.prefix),
                    selection_chars=len(request.selection),
                    suffix_chars=len(request.suffix),
                    instruction_chars=len(instruction),
                ),
            )
        except (httpx.RequestError, ValueError):
            logger.info(
                "ai_edit_suggestion_failed",
                template_id=template_id,
                prefix_len=len(request.prefix),
                selection_len=len(request.selection),
                suffix_len=len(request.suffix),
                user_id=str(actor.id),
            )
            return EditSuggestionResult(
                suggestion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="error",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(request.prefix),
                    selection_chars=len(request.selection),
                    suffix_chars=len(request.suffix),
                    instruction_chars=len(instruction),
                ),
            )

        if response.finish_reason == "length":
            return EditSuggestionResult(
                suggestion="",
                enabled=True,
                eval_meta=PromptEvalMeta(
                    template_id=template_id,
                    outcome="truncated",
                    system_prompt_chars=len(system_prompt),
                    prefix_chars=len(request.prefix),
                    selection_chars=len(request.selection),
                    suffix_chars=len(request.suffix),
                    instruction_chars=len(instruction),
                ),
            )

        suggestion = _normalize_edit_suggestion(response.suggestion)
        outcome = "ok" if suggestion else "empty"
        return EditSuggestionResult(
            suggestion=suggestion,
            enabled=True,
            eval_meta=PromptEvalMeta(
                template_id=template_id,
                outcome=outcome,
                system_prompt_chars=len(system_prompt),
                prefix_chars=len(request.prefix),
                selection_chars=len(request.selection),
                suffix_chars=len(request.suffix),
                instruction_chars=len(instruction),
            ),
        )
