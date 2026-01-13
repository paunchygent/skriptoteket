from __future__ import annotations

from typing import Literal, Protocol
from uuid import UUID

from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn

ToolSessionTurnStatus = Literal["pending", "complete", "failed", "cancelled"]


class ToolSessionTurnRepositoryProtocol(Protocol):
    async def create_turn(
        self,
        *,
        turn_id: UUID,
        tool_session_id: UUID,
        status: ToolSessionTurnStatus,
        provider: str | None,
        correlation_id: UUID | None,
        failure_outcome: str | None = None,
    ) -> ToolSessionTurn: ...

    async def get_pending_turn(self, *, tool_session_id: UUID) -> ToolSessionTurn | None: ...

    async def cancel_pending_turn(
        self,
        *,
        tool_session_id: UUID,
        failure_outcome: str,
    ) -> ToolSessionTurn | None: ...

    async def update_status(
        self,
        *,
        turn_id: UUID,
        status: ToolSessionTurnStatus,
        correlation_id: UUID | None,
        failure_outcome: str | None = None,
        provider: str | None = None,
    ) -> ToolSessionTurn | None: ...

    async def list_tail(self, *, tool_session_id: UUID, limit: int) -> list[ToolSessionTurn]: ...

    async def delete_all(self, *, tool_session_id: UUID) -> int: ...
