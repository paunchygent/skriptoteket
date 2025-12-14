from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_category import ToolCategoryModel
from skriptoteket.infrastructure.db.models.tool_profession import ToolProfessionModel
from skriptoteket.protocols.catalog import ToolRepositoryProtocol


class PostgreSQLToolRepository(ToolRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_tags(self, *, profession_id: UUID, category_id: UUID) -> list[Tool]:
        stmt = (
            select(ToolModel)
            .join(ToolProfessionModel, ToolProfessionModel.tool_id == ToolModel.id)
            .join(ToolCategoryModel, ToolCategoryModel.tool_id == ToolModel.id)
            .where(
                ToolProfessionModel.profession_id == profession_id,
                ToolCategoryModel.category_id == category_id,
            )
            .distinct()
            .order_by(ToolModel.title.asc(), ToolModel.slug.asc())
        )
        result = await self._session.execute(stmt)
        return [Tool.model_validate(model) for model in result.scalars().all()]

