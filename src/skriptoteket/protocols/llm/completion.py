"""Inline completion protocol types."""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.llm_door import AiDoorCaller

from .common import SystemMessageVariant, VirtualFileId
from .eval import PromptEvalMeta


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
    """Inline completion through the LLM provider door for ``caller``.

    Raises ``AiDailyLimitReached`` when the door refuses the call for a daily
    limit.
    """

    async def complete_inline(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
        caller: AiDoorCaller,
    ) -> LLMCompletionResponse: ...


class InlineCompletionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: InlineCompletionCommand,
    ) -> InlineCompletionResult: ...
