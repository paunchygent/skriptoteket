from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.infrastructure.db.models.tool_maintainer import ToolMaintainerModel
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol


class PostgreSQLToolMaintainerRepository(ToolMaintainerRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_maintainer(self, *, tool_id: UUID, user_id: UUID) -> bool:
        stmt = (
            select(ToolMaintainerModel)
            .where(ToolMaintainerModel.tool_id == tool_id, ToolMaintainerModel.user_id == user_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_maintainer(self, *, tool_id: UUID, user_id: UUID) -> None:
        if await self.is_maintainer(tool_id=tool_id, user_id=user_id):
            return
        self._session.add(ToolMaintainerModel(tool_id=tool_id, user_id=user_id))
        await self._session.flush()
