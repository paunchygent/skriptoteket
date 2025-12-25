from __future__ import annotations

from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.infrastructure.db.models.tool_session import ToolSessionModel
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol


class PostgreSQLToolSessionRepository(ToolSessionRepositoryProtocol):
    """PostgreSQL repository for tool session state (ADR-0024).

    Uses atomic updates for optimistic concurrency; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> ToolSession | None:
        stmt = (
            select(ToolSessionModel)
            .where(ToolSessionModel.tool_id == tool_id)
            .where(ToolSessionModel.user_id == user_id)
            .where(ToolSessionModel.context == context)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return ToolSession.model_validate(model)

    async def get_or_create(
        self,
        *,
        session_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> ToolSession:
        stmt = (
            insert(ToolSessionModel)
            .values(
                id=session_id,
                tool_id=tool_id,
                user_id=user_id,
                context=context,
                state={},
                state_rev=0,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ToolSessionModel.tool_id,
                    ToolSessionModel.user_id,
                    ToolSessionModel.context,
                ]
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return await self._get_by_key(tool_id=tool_id, user_id=user_id, context=context)

    async def update_state(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        expected_state_rev: int,
        state: dict[str, JsonValue],
    ) -> ToolSession:
        stmt = (
            update(ToolSessionModel)
            .where(ToolSessionModel.tool_id == tool_id)
            .where(ToolSessionModel.user_id == user_id)
            .where(ToolSessionModel.context == context)
            .where(ToolSessionModel.state_rev == expected_state_rev)
            .values(
                state=state,
                state_rev=ToolSessionModel.state_rev + 1,
                updated_at=func.now(),
            )
            .returning(ToolSessionModel.id)
        )
        result = await self._session.execute(stmt)
        updated_id = result.scalar_one_or_none()
        if updated_id is None:
            current_state_rev = await self._get_state_rev_or_none(
                tool_id=tool_id,
                user_id=user_id,
                context=context,
            )
            if current_state_rev is None:
                raise not_found("ToolSession", f"{tool_id}:{user_id}:{context}")

            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="ToolSession state_rev conflict",
                details={
                    "tool_id": str(tool_id),
                    "user_id": str(user_id),
                    "context": context,
                    "expected_state_rev": expected_state_rev,
                    "current_state_rev": current_state_rev,
                },
            )

        await self._session.flush()
        return await self._get_by_key(tool_id=tool_id, user_id=user_id, context=context)

    async def clear_state(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> ToolSession:
        stmt = (
            update(ToolSessionModel)
            .where(ToolSessionModel.tool_id == tool_id)
            .where(ToolSessionModel.user_id == user_id)
            .where(ToolSessionModel.context == context)
            .values(
                state={},
                state_rev=ToolSessionModel.state_rev + 1,
                updated_at=func.now(),
            )
            .returning(ToolSessionModel.id)
        )
        result = await self._session.execute(stmt)
        updated_id = result.scalar_one_or_none()
        if updated_id is None:
            raise not_found("ToolSession", f"{tool_id}:{user_id}:{context}")

        await self._session.flush()
        return await self._get_by_key(tool_id=tool_id, user_id=user_id, context=context)

    async def _get_by_key(self, *, tool_id: UUID, user_id: UUID, context: str) -> ToolSession:
        stmt = (
            select(ToolSessionModel)
            .where(ToolSessionModel.tool_id == tool_id)
            .where(ToolSessionModel.user_id == user_id)
            .where(ToolSessionModel.context == context)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise not_found("ToolSession", f"{tool_id}:{user_id}:{context}")
        return ToolSession.model_validate(model)

    async def _get_state_rev_or_none(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> int | None:
        stmt = (
            select(ToolSessionModel.state_rev)
            .where(ToolSessionModel.tool_id == tool_id)
            .where(ToolSessionModel.user_id == user_id)
            .where(ToolSessionModel.context == context)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
