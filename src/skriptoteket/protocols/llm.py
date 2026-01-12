"""LLM protocols for editor AI capabilities."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage

PromptEvalOutcome = Literal["ok", "empty", "truncated", "over_budget", "timeout", "error"]
ChatStreamDoneReason = Literal["stop", "cancelled", "error"]
ChatMessageRole = Literal["user", "assistant"]
SystemMessageVariant = Literal["info", "warning"]
VirtualFileId = Literal[
    "tool.py",
    "entrypoint.txt",
    "settings_schema.json",
    "input_schema.json",
    "usage_instructions.md",
]
EditOpKind = Literal["insert", "replace", "delete", "patch"]
EditTargetKind = Literal["cursor", "selection", "document", "anchor"]
EditAnchorPlacement = Literal["before", "after"]


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
    raw_payload: dict[str, object] | None = None


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


class EditOpsAnchor(BaseModel):
    model_config = ConfigDict(frozen=True)

    match: str = Field(min_length=1)
    placement: EditAnchorPlacement | None = None


class EditOpsCursorTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["cursor"]


class EditOpsSelectionTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["selection"]


class EditOpsDocumentTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["document"]


class EditOpsAnchorTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["anchor"]
    anchor: EditOpsAnchor


EditOpsTarget = Annotated[
    EditOpsCursorTarget | EditOpsSelectionTarget | EditOpsDocumentTarget | EditOpsAnchorTarget,
    Field(discriminator="kind"),
]


class EditOpsInsertOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["insert"]
    target_file: VirtualFileId
    target: EditOpsTarget
    content: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_insert(self) -> "EditOpsInsertOp":
        if self.target.kind not in {"cursor", "anchor"}:
            raise ValueError("Insert ops must target cursor or anchor")
        if self.target.kind == "anchor" and self.target.anchor.placement is None:
            raise ValueError("Anchor placement is required for insert ops")
        return self


class EditOpsReplaceOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["replace"]
    target_file: VirtualFileId
    target: EditOpsTarget
    content: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_replace(self) -> "EditOpsReplaceOp":
        if self.target.kind == "cursor":
            raise ValueError("Replace ops must target selection, document, or anchor")
        return self


class EditOpsDeleteOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["delete"]
    target_file: VirtualFileId
    target: EditOpsTarget
    content: None = None

    @model_validator(mode="after")
    def validate_delete(self) -> "EditOpsDeleteOp":
        if self.target.kind == "cursor":
            raise ValueError("Delete ops must target selection, document, or anchor")
        return self


class EditOpsPatchOp(BaseModel):
    model_config = ConfigDict(frozen=True)

    op: Literal["patch"]
    target_file: VirtualFileId
    patch: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_patch_shape(self) -> "EditOpsPatchOp":
        """Light validation; backend is responsible for robust sanitization + apply.

        We accept slightly malformed headers to reduce regeneration loops, but still reject
        obvious multi-file diffs and wrong-file targets when headers are present.
        """

        patch = self.patch.replace("\r\n", "\n").replace("\r", "\n")
        if "@@" not in patch:
            raise ValueError("Patch must include at least one @@ hunk header")

        def basename(path: str) -> str:
            cleaned = path
            if cleaned.startswith(("a/", "b/")):
                cleaned = cleaned[2:]
            if cleaned.startswith("./"):
                cleaned = cleaned[2:]
            return cleaned

        old_path: str | None = None
        new_path: str | None = None
        diff_git_paths: tuple[str | None, str | None] = (None, None)

        diff_git_count = 0
        header_old_count = 0
        header_new_count = 0

        for line in patch.split("\n"):
            if line.startswith("diff --git "):
                diff_git_count += 1
                parts = line.split()
                if len(parts) >= 4 and diff_git_paths == (None, None):
                    diff_git_paths = (parts[2], parts[3])
                continue

            if line.startswith("--- "):
                header_old_count += 1
                if old_path is None:
                    parts = line.split()
                    if len(parts) >= 2:
                        old_path = parts[1]
                continue

            if line.startswith("+++ "):
                header_new_count += 1
                if new_path is None:
                    parts = line.split()
                    if len(parts) >= 2:
                        new_path = parts[1]
                continue

        if diff_git_count > 1 or header_old_count > 1 or header_new_count > 1:
            raise ValueError("Patch must only touch one file")

        git_old, git_new = diff_git_paths
        if git_old and git_new:
            if git_old == "/dev/null" or git_new == "/dev/null":
                raise ValueError("Patch must not create or delete files")
            if basename(git_old) != self.target_file or basename(git_new) != self.target_file:
                raise ValueError("Patch targets a different file than target_file")

        if old_path and new_path:
            if old_path == "/dev/null" or new_path == "/dev/null":
                raise ValueError("Patch must not create or delete files")
            if basename(old_path) != self.target_file or basename(new_path) != self.target_file:
                raise ValueError("Patch targets a different file than target_file")

        return self


EditOpsOp = Annotated[
    EditOpsInsertOp | EditOpsReplaceOp | EditOpsDeleteOp | EditOpsPatchOp,
    Field(discriminator="op"),
]


class EditOpsCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str
    active_file: VirtualFileId
    selection: EditOpsSelection | None = None
    cursor: EditOpsCursor | None = None
    virtual_files: dict[VirtualFileId, str]
    allow_remote_fallback: bool = False


class EditOpsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    assistant_message: str
    ops: list[EditOpsOp]
    base_fingerprints: dict[VirtualFileId, str]
    eval_meta: PromptEvalMeta | None = None


class EditOpsPreviewCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    active_file: VirtualFileId
    selection: EditOpsSelection | None = None
    cursor: EditOpsCursor | None = None
    virtual_files: dict[VirtualFileId, str]
    ops: list[EditOpsOp]


class EditOpsPreviewMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_hash: str
    patch_id: str
    requires_confirmation: bool
    fuzz_level_used: int = 0
    max_offset: int = 0
    normalizations_applied: list[str] = Field(default_factory=list)
    applied_cleanly: bool = True


class EditOpsPreviewErrorDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    op_index: int | None = None
    target_file: VirtualFileId | None = None
    hunk_index: int | None = None
    hunk_header: str | None = None
    expected_snippet: str | None = None
    base_snippet: str | None = None


class EditOpsPreviewResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    after_virtual_files: dict[VirtualFileId, str]
    errors: list[str]
    error_details: list[EditOpsPreviewErrorDetails] = Field(default_factory=list)
    meta: EditOpsPreviewMeta


class EditOpsApplyCommand(EditOpsPreviewCommand):
    model_config = ConfigDict(frozen=True)

    base_hash: str
    patch_id: str


class EditorChatCommand(BaseModel):
    """Application command for editor chat (streaming)."""

    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    message: str
    base_version_id: UUID | None = None
    allow_remote_fallback: bool = False


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


class InlineCompletionProviderProtocol(Protocol):
    """Protocol for an OpenAI-compatible completion provider."""

    async def complete_inline(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
    ) -> LLMCompletionResponse: ...


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


class ChatStreamProvidersProtocol(Protocol):
    primary: ChatStreamProviderProtocol
    fallback: ChatStreamProviderProtocol | None
    fallback_is_remote: bool


class ChatOpsProvidersProtocol(Protocol):
    primary: ChatOpsProviderProtocol
    fallback: ChatOpsProviderProtocol | None
    fallback_is_remote: bool


class ChatOpsBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_window_tokens: int
    max_output_tokens: int


class ChatOpsBudgetResolverProtocol(Protocol):
    """Resolve prompt budgeting constraints for chat-ops (edit-ops)."""

    def resolve_chat_ops_budget(self, *, provider: "ChatFailoverProvider") -> ChatOpsBudget: ...


ChatFailoverProvider = Literal["primary", "fallback"]
ChatFailoverReason = Literal["primary_default", "sticky_fallback", "breaker_open", "load_shed"]
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
        allow_remote_fallback: bool,
        fallback_available: bool,
        fallback_is_remote: bool,
    ) -> ChatFailoverDecision: ...

    async def acquire_inflight(self, *, provider: ChatFailoverProvider) -> None: ...

    async def release_inflight(self, *, provider: ChatFailoverProvider) -> None: ...

    async def record_success(self, *, provider: ChatFailoverProvider) -> None: ...

    async def record_failure(self, *, provider: ChatFailoverProvider) -> None: ...

    async def mark_fallback_used(self, *, user_id: UUID, tool_id: UUID) -> None: ...


class InlineCompletionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: InlineCompletionCommand,
    ) -> InlineCompletionResult: ...


class EditOpsHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsCommand,
    ) -> EditOpsResult: ...


class EditOpsPreviewHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsPreviewCommand,
    ) -> EditOpsPreviewResult: ...


class EditOpsApplyHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: EditOpsApplyCommand,
    ) -> EditOpsPreviewResult: ...


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
