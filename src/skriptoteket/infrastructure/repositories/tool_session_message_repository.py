from __future__ import annotations

from typing import cast
from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.tool_session_messages import ChatMessageRole, ToolSessionMessage
from skriptoteket.infrastructure.db.models.tool_session_message import ToolSessionMessageModel
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol


class PostgreSQLToolSessionMessageRepository(ToolSessionMessageRepositoryProtocol):
    """PostgreSQL repository for editor chat messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append_message(
        self,
        *,
        tool_session_id: UUID,
        message_id: UUID,
        role: ChatMessageRole,
        content: str,
        meta: dict[str, JsonValue] | None = None,
    ) -> ToolSessionMessage:
        model = ToolSessionMessageModel(
            tool_session_id=tool_session_id,
            message_id=message_id,
            role=role,
            content=content,
            meta=meta,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ToolSessionMessage.model_validate(model)

    async def list_tail(self, *, tool_session_id: UUID, limit: int) -> list[ToolSessionMessage]:
        stmt = (
            select(ToolSessionMessageModel)
            .where(ToolSessionMessageModel.tool_session_id == tool_session_id)
            .order_by(ToolSessionMessageModel.sequence.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return [ToolSessionMessage.model_validate(row) for row in rows]

    async def get_by_message_id(
        self, *, tool_session_id: UUID, message_id: UUID
    ) -> ToolSessionMessage | None:
        stmt = (
            select(ToolSessionMessageModel)
            .where(ToolSessionMessageModel.tool_session_id == tool_session_id)
            .where(ToolSessionMessageModel.message_id == message_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return ToolSessionMessage.model_validate(model)

    async def delete_all(self, *, tool_session_id: UUID) -> int:
        stmt = delete(ToolSessionMessageModel).where(
            ToolSessionMessageModel.tool_session_id == tool_session_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(cast(CursorResult[object], result).rowcount or 0)
