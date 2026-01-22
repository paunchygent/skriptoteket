"""Chat and streaming protocol types."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn

from .common import SystemMessageVariant, VirtualFileId

ChatStreamDoneReason = Literal["stop", "cancelled", "error"]
ChatMessageRole = Literal["user", "assistant"]


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: ChatMessageRole
    content: str
    message_id: UUID | None = None
    in_reply_to: UUID | None = None
    meta: dict[str, JsonValue] | None = None


class LLMChatRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    messages: list[ChatMessage]


class LLMChatOpsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
    finish_reason: str | None = None
    raw_payload: dict[str, object] | None = None


class EditorChatCommand(BaseModel):
    """Application command for editor chat (streaming)."""

    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str
    base_version_id: UUID | None = None
    allow_remote_fallback: bool | None = None
    active_file: VirtualFileId | None = None
    virtual_files: dict[VirtualFileId, str] | None = None


class EditorChatHistoryQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    limit: int = 60


class EditorChatHistoryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    turns: list[ToolSessionTurn]
    messages: list[ToolSessionMessage]
    base_version_id: UUID | None = None


class EditorChatClearCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class EditorChatMetaData(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: Literal[True] = True
    correlation_id: UUID | None = None
    turn_id: UUID | None = None
    assistant_message_id: UUID | None = None


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
    code: str | None = None


class EditorChatNoticeData(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str
    variant: SystemMessageVariant = "info"


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


class EditorChatNoticeEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event: Literal["notice"] = "notice"
    data: EditorChatNoticeData


EditorChatStreamEvent = (
    EditorChatMetaEvent | EditorChatNoticeEvent | EditorChatDeltaEvent | EditorChatDoneEvent
)


class ChatStreamProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible streaming chat provider."""

    def stream_chat(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
    ) -> AsyncIterator[str]: ...


class ChatStreamProvidersProtocol(Protocol):
    primary: ChatStreamProviderProtocol
    fallback: ChatStreamProviderProtocol | None
    fallback_is_remote: bool


class ChatOpsProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible chat ops provider."""

    async def complete_chat_ops(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
    ) -> LLMChatOpsResponse: ...


class ChatOpsProvidersProtocol(Protocol):
    primary: ChatOpsProviderProtocol
    fallback: ChatOpsProviderProtocol | None
    fallback_is_remote: bool


class ChatBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_window_tokens: int
    max_output_tokens: int


class ChatBudgetResolverProtocol(Protocol):
    """Resolve prompt budgeting constraints for streaming chat."""

    def resolve_chat_budget(self, *, provider: "ChatFailoverProvider") -> ChatBudget: ...


class ChatOpsBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_window_tokens: int
    max_output_tokens: int


class ChatOpsBudgetResolverProtocol(Protocol):
    """Resolve prompt budgeting constraints for chat-ops (edit-ops)."""

    def resolve_chat_ops_budget(self, *, provider: "ChatFailoverProvider") -> ChatOpsBudget: ...


ChatFailoverProvider = Literal["primary", "fallback"]
ChatFailoverReason = Literal[
    "primary_default",
    "sticky_fallback",
    "breaker_open",
    "load_shed",
    "preflight_over_budget",
]
ChatFailoverBlock = Literal["remote_fallback_required"]


class ChatFailoverDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: ChatFailoverProvider
    reason: ChatFailoverReason
    blocked: ChatFailoverBlock | None = None


class ChatFailoverRouterProtocol(Protocol):
    async def decide_route(
        self,
        *,
        user_id: UUID,
        tool_id: UUID,
        allow_remote_fallback: bool | None,
        fallback_available: bool,
        fallback_is_remote: bool,
    ) -> ChatFailoverDecision: ...

    async def acquire_inflight(self, *, provider: ChatFailoverProvider) -> None: ...

    async def release_inflight(self, *, provider: ChatFailoverProvider) -> None: ...

    async def record_success(self, *, provider: ChatFailoverProvider) -> None: ...

    async def record_failure(self, *, provider: ChatFailoverProvider) -> None: ...

    async def mark_fallback_used(self, *, user_id: UUID, tool_id: UUID) -> None: ...


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


class EditorChatHistoryHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        query: EditorChatHistoryQuery,
    ) -> EditorChatHistoryResult: ...


class ChatInFlightGuardProtocol(Protocol):
    async def try_acquire(self, *, user_id: UUID, tool_id: UUID) -> bool: ...

    async def release(self, *, user_id: UUID, tool_id: UUID) -> None: ...
