from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.infrastructure.db.models.draft_lock import DraftLockModel
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol


class PostgreSQLDraftLockRepository(DraftLockRepositoryProtocol):
    """PostgreSQL repository for draft head locks.

    Uses a request-scoped AsyncSession; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_tool(self, *, tool_id: UUID) -> DraftLock | None:
        stmt = select(DraftLockModel).where(DraftLockModel.tool_id == tool_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return DraftLock.model_validate(model)

    async def upsert(self, *, lock: DraftLock) -> DraftLock:
        stmt = (
            insert(DraftLockModel)
            .values(
                tool_id=lock.tool_id,
                draft_head_id=lock.draft_head_id,
                locked_by_user_id=lock.locked_by_user_id,
                locked_at=lock.locked_at,
                expires_at=lock.expires_at,
                forced_by_user_id=lock.forced_by_user_id,
            )
            .on_conflict_do_update(
                index_elements=[DraftLockModel.tool_id],
                set_={
                    "draft_head_id": lock.draft_head_id,
                    "locked_by_user_id": lock.locked_by_user_id,
                    "locked_at": lock.locked_at,
                    "expires_at": lock.expires_at,
                    "forced_by_user_id": lock.forced_by_user_id,
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return await self._get_by_tool_id(tool_id=lock.tool_id)

    async def delete(self, *, tool_id: UUID) -> None:
        await self._session.execute(delete(DraftLockModel).where(DraftLockModel.tool_id == tool_id))
        await self._session.flush()

    async def _get_by_tool_id(self, *, tool_id: UUID) -> DraftLock:
        stmt = select(DraftLockModel).where(DraftLockModel.tool_id == tool_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        return DraftLock.model_validate(model)
