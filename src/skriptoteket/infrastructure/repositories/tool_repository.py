from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import validation_error
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_category import ToolCategoryModel
from skriptoteket.infrastructure.db.models.tool_profession import ToolProfessionModel
from skriptoteket.protocols.catalog import ToolRepositoryProtocol


class PostgreSQLToolRepository(ToolRepositoryProtocol):
    """PostgreSQL repository for tools (catalog entries).

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

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

    async def list_all(self) -> list[Tool]:
        stmt = select(ToolModel).order_by(ToolModel.title.asc(), ToolModel.slug.asc())
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

    async def set_published(self, *, tool_id: UUID, is_published: bool, now: datetime) -> Tool:
        stmt = select(ToolModel).where(ToolModel.id == tool_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()

        model.is_published = is_published
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return Tool.model_validate(model)

    async def set_active_version_id(
        self,
        *,
        tool_id: UUID,
        active_version_id: UUID | None,
        now: datetime,
    ) -> Tool:
        stmt = select(ToolModel).where(ToolModel.id == tool_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()

        model.active_version_id = active_version_id
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return Tool.model_validate(model)

    async def update_metadata(
        self,
        *,
        tool_id: UUID,
        title: str,
        summary: str | None,
        now: datetime,
    ) -> Tool:
        stmt = select(ToolModel).where(ToolModel.id == tool_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()

        model.title = title
        model.summary = summary
        model.updated_at = now
        await self._session.flush()
        await self._session.refresh(model)
        return Tool.model_validate(model)

    async def update_slug(
        self,
        *,
        tool_id: UUID,
        slug: str,
        now: datetime,
    ) -> Tool:
        stmt = select(ToolModel).where(ToolModel.id == tool_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()

        model.slug = slug
        model.updated_at = now
        try:
            await self._session.flush()
        except IntegrityError:
            raise validation_error(
                f'Slug "{slug}" används redan. Välj en annan.',
                details={"slug": slug},
            ) from None
        await self._session.refresh(model)
        return Tool.model_validate(model)

    async def create_draft(
        self,
        *,
        tool: Tool,
        profession_ids: list[UUID],
        category_ids: list[UUID],
    ) -> Tool:
        model = ToolModel(
            id=tool.id,
            owner_user_id=tool.owner_user_id,
            slug=tool.slug,
            title=tool.title,
            summary=tool.summary,
            is_published=False,
            active_version_id=tool.active_version_id,
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

    async def list_tag_ids(
        self,
        *,
        tool_id: UUID,
    ) -> tuple[list[UUID], list[UUID]]:
        professions_stmt = (
            select(ToolProfessionModel.profession_id)
            .where(ToolProfessionModel.tool_id == tool_id)
            .order_by(ToolProfessionModel.profession_id.asc())
        )
        categories_stmt = (
            select(ToolCategoryModel.category_id)
            .where(ToolCategoryModel.tool_id == tool_id)
            .order_by(ToolCategoryModel.category_id.asc())
        )

        professions_result = await self._session.execute(professions_stmt)
        categories_result = await self._session.execute(categories_stmt)

        profession_ids = list(professions_result.scalars().all())
        category_ids = list(categories_result.scalars().all())
        return profession_ids, category_ids

    async def replace_tags(
        self,
        *,
        tool_id: UUID,
        profession_ids: list[UUID],
        category_ids: list[UUID],
        now: datetime,
    ) -> None:
        await self._session.execute(
            delete(ToolProfessionModel).where(ToolProfessionModel.tool_id == tool_id)
        )
        await self._session.execute(
            delete(ToolCategoryModel).where(ToolCategoryModel.tool_id == tool_id)
        )

        if profession_ids:
            self._session.add_all(
                [
                    ToolProfessionModel(tool_id=tool_id, profession_id=profession_id)
                    for profession_id in profession_ids
                ]
            )
        if category_ids:
            self._session.add_all(
                [
                    ToolCategoryModel(tool_id=tool_id, category_id=category_id)
                    for category_id in category_ids
                ]
            )

        await self._session.execute(
            update(ToolModel).where(ToolModel.id == tool_id).values(updated_at=now)
        )
        await self._session.flush()
