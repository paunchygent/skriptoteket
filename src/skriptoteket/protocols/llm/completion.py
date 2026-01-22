"""Inline completion protocol types."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import User

from .common import SystemMessageVariant, VirtualFileId
from .eval import PromptEvalMeta

InlineCompletionProviderPreference = Literal["local", "external"]


class LLMCompletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    prefix: str
    suffix: str
    active_file: VirtualFileId = "tool.py"


class LLMCompletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    completion: str
    finish_reason: str | None = None


class InlineCompletionCommand(BaseModel):
    """Application command for editor inline completions (ghost text)."""

    model_config = ConfigDict(frozen=True)

    prefix: str
    suffix: str
    active_file: VirtualFileId = "tool.py"
    allow_remote_fallback: bool | None = None
    inline_completion_provider: InlineCompletionProviderPreference | None = None


class InlineCompletionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    completion: str
    enabled: bool
    replace_suffix_chars: int | None = None
    notice_message: str | None = None
    notice_variant: SystemMessageVariant | None = None
    notice_code: str | None = None
    eval_meta: PromptEvalMeta | None = None


class InlineCompletionProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible completion provider."""

    async def complete_inline(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
    ) -> LLMCompletionResponse: ...


class InlineCompletionProvidersProtocol(Protocol):
    primary: InlineCompletionProviderProtocol
    primary_is_remote: bool
    fallback: InlineCompletionProviderProtocol | None
    fallback_is_remote: bool


class InlineCompletionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: InlineCompletionCommand,
    ) -> InlineCompletionResult: ...
