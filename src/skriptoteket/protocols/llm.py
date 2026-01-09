"""LLM protocols for editor AI capabilities."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage

PromptEvalOutcome = Literal["ok", "empty", "truncated", "over_budget", "timeout", "error"]
ChatStreamDoneReason = Literal["stop", "cancelled", "error"]
ChatMessageRole = Literal["user", "assistant"]
VirtualFileId = Literal[
    "tool.py",
    "entrypoint.txt",
    "settings_schema.json",
    "input_schema.json",
    "usage_instructions.md",
]
EditOpKind = Literal["insert", "replace", "delete"]
EditTargetKind = Literal["cursor", "selection", "document"]


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


class LLMChatOpsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
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


class EditOpsSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    start: int
    end: int

    @model_validator(mode="after")
    def validate_range(self) -> "EditOpsSelection":
        if self.end < self.start:
            raise ValueError("Selection end must be >= start")
        return self


class EditOpsCursor(BaseModel):
    model_config = ConfigDict(frozen=True)

    pos: int


class EditOpsTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: EditTargetKind


class EditOpsOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: EditOpKind
    target_file: VirtualFileId
    target: EditOpsTarget
    content: str | None = None

    @model_validator(mode="after")
    def validate_content(self) -> "EditOpsOp":
        if self.op in {"insert", "replace"} and not self.content:
            raise ValueError("Content is required for insert/replace ops")
        if self.op == "delete" and self.content:
            raise ValueError("Content must be omitted for delete ops")
        if self.op == "insert" and self.target.kind != "cursor":
            raise ValueError("Insert ops must target cursor")
        if self.op in {"replace", "delete"} and self.target.kind == "cursor":
            raise ValueError("Replace/delete ops must target selection or document")
        return self


class EditOpsCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str
    active_file: VirtualFileId
    selection: EditOpsSelection | None = None
    cursor: EditOpsCursor | None = None
    virtual_files: dict[VirtualFileId, str]


class EditOpsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    assistant_message: str
    ops: list[EditOpsOp]
    base_fingerprints: dict[VirtualFileId, str]
    eval_meta: PromptEvalMeta | None = None


class EditorChatCommand(BaseModel):
    """Application command for editor chat (streaming)."""

    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str
    base_version_id: UUID | None = None


class EditorChatHistoryQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    limit: int = 60


class EditorChatHistoryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    messages: list[ToolSessionMessage]
    base_version_id: UUID | None = None


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


class ChatOpsProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible chat ops provider."""

    async def complete_chat_ops(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
    ) -> LLMChatOpsResponse: ...


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


class EditOpsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsCommand,
    ) -> EditOpsResult: ...


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
