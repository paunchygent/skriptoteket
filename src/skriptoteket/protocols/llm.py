"""LLM protocols for editor AI capabilities."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import User

PromptEvalOutcome = Literal["ok", "empty", "truncated", "over_budget", "timeout", "error"]


class PromptEvalMeta(BaseModel):
    """Evaluation-only metadata (never includes prompts/code/model output text)."""

    model_config = ConfigDict(frozen=True)

    template_id: str | None
    outcome: PromptEvalOutcome
    system_prompt_chars: int
    prefix_chars: int = 0
    suffix_chars: int = 0
    instruction_chars: int = 0
    selection_chars: int = 0


class LLMCompletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefix: str
    suffix: str


class LLMCompletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    completion: str
    finish_reason: str | None = None


class LLMEditRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefix: str
    selection: str
    suffix: str
    instruction: str | None = None


class LLMEditResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion: str
    finish_reason: str | None = None


class InlineCompletionCommand(BaseModel):
    """Application command for editor inline completions (ghost text)."""

    model_config = ConfigDict(frozen=True)

    prefix: str
    suffix: str


class InlineCompletionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    completion: str
    enabled: bool
    eval_meta: PromptEvalMeta | None = None


class EditSuggestionCommand(BaseModel):
    """Application command for editor edit suggestions."""

    model_config = ConfigDict(frozen=True)

    prefix: str
    selection: str
    suffix: str
    instruction: str | None = None


class EditSuggestionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    suggestion: str
    enabled: bool
    eval_meta: PromptEvalMeta | None = None


class InlineCompletionProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible completion provider."""

    async def complete_inline(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
    ) -> LLMCompletionResponse: ...


class EditSuggestionProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible edit provider."""

    async def suggest_edits(
        self,
        *,
        request: LLMEditRequest,
        system_prompt: str,
    ) -> LLMEditResponse: ...


class InlineCompletionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: InlineCompletionCommand,
    ) -> InlineCompletionResult: ...


class EditSuggestionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditSuggestionCommand,
    ) -> EditSuggestionResult: ...
