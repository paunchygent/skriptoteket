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
                ToolModel.is_published.is_(True),
            )
            .distinct()
            .order_by(ToolModel.title.asc(), ToolModel.slug.asc())
        )
        result = await self._session.execute(stmt)
        return [Tool.model_validate(model) for model in result.scalars().all()]

    async def get_by_id(self, *, tool_id: UUID) -> Tool | None:
        stmt = select(ToolModel).where(ToolModel.id == tool_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return Tool.model_validate(model) if model else None

    async def get_by_slug(self, *, slug: str) -> Tool | None:
        stmt = select(ToolModel).where(ToolModel.slug == slug)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return Tool.model_validate(model) if model else None

    async def create_draft(
        self,
        *,
        tool: Tool,
        profession_ids: list[UUID],
        category_ids: list[UUID],
    ) -> Tool:
        model = ToolModel(
            id=tool.id,
            slug=tool.slug,
            title=tool.title,
            summary=tool.summary,
            is_published=False,
            created_at=tool.created_at,
            updated_at=tool.updated_at,
        )
        self._session.add(model)
        self._session.add_all(
            [
                ToolProfessionModel(tool_id=tool.id, profession_id=profession_id)
                for profession_id in profession_ids
            ]
        )
        self._session.add_all(
            [
                ToolCategoryModel(tool_id=tool.id, category_id=category_id)
                for category_id in category_ids
            ]
        )
        await self._session.flush()
        await self._session.refresh(model)
        return Tool.model_validate(model)
