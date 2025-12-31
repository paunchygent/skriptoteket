"""LLM protocols for editor AI capabilities."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import User


class LLMCompletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefix: str
    suffix: str


class LLMCompletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    completion: str
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


class InlineCompletionProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible completion provider."""

    async def complete_inline(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
    ) -> LLMCompletionResponse: ...


class InlineCompletionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: InlineCompletionCommand,
    ) -> InlineCompletionResult: ...
