from __future__ import annotations

from typing import cast
from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import and_, case, delete, exists, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.tool_session_messages import ChatMessageRole, ToolSessionMessage
from skriptoteket.infrastructure.db.models.tool_session_message import ToolSessionMessageModel
from skriptoteket.infrastructure.db.models.tool_session_turn import ToolSessionTurnModel
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol


class PostgreSQLToolSessionMessageRepository(ToolSessionMessageRepositoryProtocol):
    """PostgreSQL repository for editor chat messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_message(
        self,
        *,
        tool_session_id: UUID,
        turn_id: UUID,
        message_id: UUID,
        role: ChatMessageRole,
        content: str,
        meta: dict[str, JsonValue] | None = None,
    ) -> ToolSessionMessage:
        model = ToolSessionMessageModel(
            tool_session_id=tool_session_id,
            turn_id=turn_id,
            message_id=message_id,
            role=role,
            content=content,
            meta=meta,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ToolSessionMessage.model_validate(model)

    async def update_message_content_if_pending_turn(
        self,
        *,
        tool_session_id: UUID,
        turn_id: UUID,
        message_id: UUID,
        content: str,
        correlation_id: UUID | None,
        meta: dict[str, JsonValue] | None = None,
    ) -> bool:
        turn_guard = (
            select(ToolSessionTurnModel.id)
            .where(ToolSessionTurnModel.tool_session_id == tool_session_id)
            .where(ToolSessionTurnModel.id == turn_id)
            .where(ToolSessionTurnModel.status == "pending")
        )
        if correlation_id is not None:
            turn_guard = turn_guard.where(ToolSessionTurnModel.correlation_id == correlation_id)

        values: dict[str, object] = {"content": content}
        if meta is not None:
            values["meta"] = meta

        stmt = (
            update(ToolSessionMessageModel)
            .where(ToolSessionMessageModel.tool_session_id == tool_session_id)
            .where(ToolSessionMessageModel.turn_id == turn_id)
            .where(ToolSessionMessageModel.message_id == message_id)
            .where(exists(turn_guard))
            .values(**values)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return bool(cast(CursorResult[object], result).rowcount)

    async def list_by_turn_ids(
        self,
        *,
        tool_session_id: UUID,
        turn_ids: list[UUID],
    ) -> list[ToolSessionMessage]:
        if not turn_ids:
            return []

        role_order = case((ToolSessionMessageModel.role == "user", 0), else_=1)

        stmt = (
            select(ToolSessionMessageModel)
            .join(
                ToolSessionTurnModel,
                and_(
                    ToolSessionTurnModel.tool_session_id == ToolSessionMessageModel.tool_session_id,
                    ToolSessionTurnModel.id == ToolSessionMessageModel.turn_id,
                ),
            )
            .where(ToolSessionMessageModel.tool_session_id == tool_session_id)
            .where(ToolSessionMessageModel.turn_id.in_(turn_ids))
            .order_by(ToolSessionTurnModel.sequence.asc(), role_order.asc())
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
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
