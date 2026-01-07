"""LLM protocols for editor AI capabilities."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import User

PromptEvalOutcome = Literal["ok", "empty", "truncated", "over_budget", "timeout", "error"]
ChatStreamDoneReason = Literal["stop", "cancelled", "error"]
ChatMessageRole = Literal["user", "assistant"]


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


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: ChatMessageRole
    content: str
    message_id: UUID | None = None
    in_reply_to: UUID | None = None


class LLMChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    messages: list[ChatMessage]


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


class EditorChatCommand(BaseModel):
    """Application command for editor chat (streaming)."""

    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str


class EditorChatClearCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class EditorChatMetaData(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: Literal[True] = True


class EditorChatDeltaData(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str


class EditorChatDoneEnabledData(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: Literal[True] = True
    reason: ChatStreamDoneReason


class EditorChatDoneDisabledData(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: Literal[False] = False
    message: str


class EditorChatMetaEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: Literal["meta"] = "meta"
    data: EditorChatMetaData


class EditorChatDeltaEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: Literal["delta"] = "delta"
    data: EditorChatDeltaData


class EditorChatDoneEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: Literal["done"] = "done"
    data: EditorChatDoneEnabledData | EditorChatDoneDisabledData


EditorChatStreamEvent = EditorChatMetaEvent | EditorChatDeltaEvent | EditorChatDoneEvent


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


class ChatStreamProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible streaming chat provider."""

    def stream_chat(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
    ) -> AsyncIterator[str]: ...


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


class EditorChatHandlerProtocol(Protocol):
    def stream(
        self,
        *,
        actor: User,
        command: EditorChatCommand,
    ) -> AsyncIterator[EditorChatStreamEvent]: ...


class EditorChatClearHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditorChatClearCommand,
    ) -> None: ...


class ChatInFlightGuardProtocol(Protocol):
    async def try_acquire(self, *, user_id: UUID, tool_id: UUID) -> bool: ...

    async def release(self, *, user_id: UUID, tool_id: UUID) -> None: ...
