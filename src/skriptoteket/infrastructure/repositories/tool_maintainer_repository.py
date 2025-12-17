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

    async def list_maintainers(self, *, tool_id: UUID) -> list[UUID]:
        stmt = select(ToolMaintainerModel.user_id).where(ToolMaintainerModel.tool_id == tool_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def remove_maintainer(self, *, tool_id: UUID, user_id: UUID) -> None:
        # We fetch the model instance to delete it, although delete() statement could also work.
        # Fetching allows ensuring it exists if strictness is required, but here we just want it
        # gone.
        # Direct delete is more efficient.
        # However, ORM delete is often safer with cascading, though this is a simple join table.
        # Let's use the object approach for consistency with potential future event hooks.
        stmt = select(ToolMaintainerModel).where(
            ToolMaintainerModel.tool_id == tool_id, ToolMaintainerModel.user_id == user_id
        )
        result = await self._session.execute(stmt)
        maintainer = result.scalar_one_or_none()
        if maintainer:
            await self._session.delete(maintainer)
            await self._session.flush()

    async def list_tools_for_user(self, *, user_id: UUID) -> list[UUID]:
        stmt = select(ToolMaintainerModel.tool_id).where(ToolMaintainerModel.user_id == user_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
