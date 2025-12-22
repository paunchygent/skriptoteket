from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.catalog.models import Profession
from skriptoteket.infrastructure.db.models.profession import ProfessionModel
from skriptoteket.protocols.catalog import ProfessionRepositoryProtocol


class PostgreSQLProfessionRepository(ProfessionRepositoryProtocol):
    """PostgreSQL repository for professions.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Profession]:
        stmt = select(ProfessionModel).order_by(
            ProfessionModel.sort_order.asc(),
            ProfessionModel.slug.asc(),
        )
        result = await self._session.execute(stmt)
        return [Profession.model_validate(model) for model in result.scalars().all()]

    async def get_by_slug(self, slug: str) -> Profession | None:
        stmt = select(ProfessionModel).where(ProfessionModel.slug == slug)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return Profession.model_validate(model) if model else None

    async def list_by_ids(self, *, profession_ids: list[UUID]) -> list[Profession]:
        if not profession_ids:
            return []
        stmt = select(ProfessionModel).where(ProfessionModel.id.in_(profession_ids))
        result = await self._session.execute(stmt)
        return [Profession.model_validate(model) for model in result.scalars().all()]
