from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.catalog.models import Category
from skriptoteket.infrastructure.db.models.category import CategoryModel
from skriptoteket.infrastructure.db.models.profession_category import ProfessionCategoryModel
from skriptoteket.protocols.catalog import CategoryRepositoryProtocol


class PostgreSQLCategoryRepository(CategoryRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_profession(self, *, profession_id: UUID) -> list[Category]:
        stmt = (
            select(CategoryModel)
            .join(ProfessionCategoryModel, ProfessionCategoryModel.category_id == CategoryModel.id)
            .where(ProfessionCategoryModel.profession_id == profession_id)
            .order_by(ProfessionCategoryModel.sort_order.asc(), CategoryModel.slug.asc())
        )
        result = await self._session.execute(stmt)
        return [Category.model_validate(model) for model in result.scalars().all()]

    async def get_for_profession_by_slug(
        self, *, profession_id: UUID, category_slug: str
    ) -> Category | None:
        stmt = (
            select(CategoryModel)
            .join(ProfessionCategoryModel, ProfessionCategoryModel.category_id == CategoryModel.id)
            .where(
                ProfessionCategoryModel.profession_id == profession_id,
                CategoryModel.slug == category_slug,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return Category.model_validate(model) if model else None

