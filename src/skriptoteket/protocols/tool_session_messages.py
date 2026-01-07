from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.scripting.tool_session_messages import (
    ChatMessageRole,
    ToolSessionMessage,
)


class ToolSessionMessageRepositoryProtocol(Protocol):
    async def append_message(
        self,
        *,
        tool_session_id: UUID,
        message_id: UUID,
        role: ChatMessageRole,
        content: str,
        meta: dict[str, JsonValue] | None = None,
    ) -> ToolSessionMessage: ...

    async def list_tail(self, *, tool_session_id: UUID, limit: int) -> list[ToolSessionMessage]: ...

    async def get_by_message_id(
        self, *, tool_session_id: UUID, message_id: UUID
    ) -> ToolSessionMessage | None: ...

    async def delete_all(self, *, tool_session_id: UUID) -> int: ...
