from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn
from skriptoteket.infrastructure.db.models.tool_session_turn import ToolSessionTurnModel
from skriptoteket.protocols.tool_session_turns import (
    ToolSessionTurnRepositoryProtocol,
    ToolSessionTurnStatus,
)


class PostgreSQLToolSessionTurnRepository(ToolSessionTurnRepositoryProtocol):
    """PostgreSQL repository for editor chat turns."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_turn(
        self,
        *,
        turn_id: UUID,
        tool_session_id: UUID,
        status: ToolSessionTurnStatus,
        provider: str | None,
        correlation_id: UUID | None,
        failure_outcome: str | None = None,
    ) -> ToolSessionTurn:
        model = ToolSessionTurnModel(
            id=turn_id,
            tool_session_id=tool_session_id,
            status=status,
            failure_outcome=failure_outcome,
            provider=provider,
            correlation_id=correlation_id,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ToolSessionTurn.model_validate(model)

    async def get_pending_turn(self, *, tool_session_id: UUID) -> ToolSessionTurn | None:
        stmt = (
            select(ToolSessionTurnModel)
            .where(ToolSessionTurnModel.tool_session_id == tool_session_id)
            .where(ToolSessionTurnModel.status == "pending")
            .order_by(ToolSessionTurnModel.sequence.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return ToolSessionTurn.model_validate(model) if model is not None else None

    async def cancel_pending_turn(
        self,
        *,
        tool_session_id: UUID,
        failure_outcome: str,
    ) -> ToolSessionTurn | None:
        stmt = (
            update(ToolSessionTurnModel)
            .where(ToolSessionTurnModel.tool_session_id == tool_session_id)
            .where(ToolSessionTurnModel.status == "pending")
            .values(
                status="cancelled",
                failure_outcome=failure_outcome,
                updated_at=func.now(),
            )
            .returning(ToolSessionTurnModel.id)
        )
        result = await self._session.execute(stmt)
        updated_id = result.scalar_one_or_none()
        if updated_id is None:
            return None
        await self._session.flush()
        return await self._get_by_id(turn_id=updated_id)

    async def update_status(
        self,
        *,
        turn_id: UUID,
        status: ToolSessionTurnStatus,
        correlation_id: UUID | None,
        failure_outcome: str | None = None,
        provider: str | None = None,
    ) -> ToolSessionTurn | None:
        stmt = (
            update(ToolSessionTurnModel)
            .where(ToolSessionTurnModel.id == turn_id)
            .where(ToolSessionTurnModel.status == "pending")
            .values(
                status=status,
                failure_outcome=failure_outcome,
                provider=provider,
                updated_at=func.now(),
            )
            .returning(ToolSessionTurnModel.id)
        )
        if correlation_id is not None:
            stmt = stmt.where(ToolSessionTurnModel.correlation_id == correlation_id)
        result = await self._session.execute(stmt)
        updated_id = result.scalar_one_or_none()
        if updated_id is None:
            return None
        await self._session.flush()
        return await self._get_by_id(turn_id=updated_id)

    async def list_tail(self, *, tool_session_id: UUID, limit: int) -> list[ToolSessionTurn]:
        stmt = (
            select(ToolSessionTurnModel)
            .where(ToolSessionTurnModel.tool_session_id == tool_session_id)
            .order_by(ToolSessionTurnModel.sequence.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return [ToolSessionTurn.model_validate(row) for row in rows]

    async def delete_all(self, *, tool_session_id: UUID) -> int:
        stmt = delete(ToolSessionTurnModel).where(
            ToolSessionTurnModel.tool_session_id == tool_session_id
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(cast(CursorResult[object], result).rowcount or 0)

    async def _get_by_id(self, *, turn_id: UUID) -> ToolSessionTurn:
        stmt = select(ToolSessionTurnModel).where(ToolSessionTurnModel.id == turn_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        return ToolSessionTurn.model_validate(model)
