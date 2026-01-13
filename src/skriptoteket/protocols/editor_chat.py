from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.llm import (
    ChatFailoverDecision,
    ChatMessage,
    EditorChatCommand,
    EditorChatStreamEvent,
    LLMChatRequest,
    VirtualFileId,
)
from skriptoteket.protocols.token_counter import TokenCounterProtocol


@dataclass(frozen=True, slots=True)
class PreparedEditorChatRequest:
    request: LLMChatRequest
    system_prompt: str
    tool_session_id: UUID
    turn_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    correlation_id: UUID | None


class EditorChatPromptBuilderProtocol(Protocol):
    def plan_max_user_message_tokens(
        self, *, system_prompt: str, token_counter: TokenCounterProtocol
    ) -> int | None: ...

    def validate_plain_user_message(
        self,
        *,
        message: str,
        max_user_message_tokens: int,
        token_counter: TokenCounterProtocol,
    ) -> None: ...

    def build_user_payload_message(
        self,
        *,
        message: str,
        active_file: VirtualFileId | None,
        virtual_files: dict[VirtualFileId, str],
        max_user_message_tokens: int,
        token_counter: TokenCounterProtocol,
    ) -> ChatMessage: ...

    def build_llm_request(
        self,
        *,
        system_prompt: str,
        existing_messages: list[ChatMessage],
        message: str,
        user_payload_message: ChatMessage | None,
        token_counter: TokenCounterProtocol,
    ) -> LLMChatRequest: ...


class EditorChatTurnPreparerProtocol(Protocol):
    async def prepare(
        self,
        *,
        actor: User,
        command: EditorChatCommand,
        system_prompt: str,
        token_counter: TokenCounterProtocol,
    ) -> PreparedEditorChatRequest: ...


class EditorChatStreamOrchestratorProtocol(Protocol):
    def stream(
        self,
        *,
        actor: User,
        command: EditorChatCommand,
        prepared: PreparedEditorChatRequest,
        decision: ChatFailoverDecision,
        template_id: str,
    ) -> AsyncIterator[EditorChatStreamEvent]: ...
