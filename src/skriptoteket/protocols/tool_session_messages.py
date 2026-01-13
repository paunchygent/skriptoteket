from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.scripting.tool_session_messages import (
    ChatMessageRole,
    ToolSessionMessage,
)


class ToolSessionMessageRepositoryProtocol(Protocol):
    async def create_message(
        self,
        *,
        tool_session_id: UUID,
        turn_id: UUID,
        message_id: UUID,
        role: ChatMessageRole,
        content: str,
        meta: dict[str, JsonValue] | None = None,
    ) -> ToolSessionMessage: ...

    async def update_message_content_if_pending_turn(
        self,
        *,
        tool_session_id: UUID,
        turn_id: UUID,
        message_id: UUID,
        content: str,
        correlation_id: UUID | None,
        meta: dict[str, JsonValue] | None = None,
    ) -> bool: ...

    async def list_by_turn_ids(
        self,
        *,
        tool_session_id: UUID,
        turn_ids: list[UUID],
    ) -> list[ToolSessionMessage]: ...

    async def get_by_message_id(
        self, *, tool_session_id: UUID, message_id: UUID
    ) -> ToolSessionMessage | None: ...

    async def delete_all(self, *, tool_session_id: UUID) -> int: ...
