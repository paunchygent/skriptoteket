"""PostgreSQL repository for blocked registration domains.

Purpose:
  Persist and query normalized blocklist root domains without taking over
  transaction ownership from the unit of work.

Relationships:
  - Uses `BlockedDomainModel` for SQLAlchemy persistence.
  - Implements `BlockedDomainRepositoryProtocol`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import BlockedDomain
from skriptoteket.infrastructure.db.models.blocked_domain import BlockedDomainModel
from skriptoteket.protocols.identity import BlockedDomainRepositoryProtocol


class PostgreSQLBlockedDomainRepository(BlockedDomainRepositoryProtocol):
    """Persist blocklist rows inside the active SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_domain(self, domain: str) -> BlockedDomain | None:
        model = await self._session.get(BlockedDomainModel, domain)
        return BlockedDomain.model_validate(model) if model else None

    async def upsert(self, *, domain: BlockedDomain) -> BlockedDomain:
        model = await self._session.get(BlockedDomainModel, domain.domain)
        if model is None:
            model = BlockedDomainModel(
                domain=domain.domain,
                reason=domain.reason,
                source=domain.source,
                source_ref=domain.source_ref,
                is_active=domain.is_active,
                notes=domain.notes,
                created_at=domain.created_at,
                updated_at=domain.updated_at,
            )
            self._session.add(model)
        else:
            model.reason = domain.reason
            model.source = domain.source
            model.source_ref = domain.source_ref
            model.is_active = domain.is_active
            model.notes = domain.notes
            model.updated_at = domain.updated_at

        await self._session.flush()
        await self._session.refresh(model)
        return BlockedDomain.model_validate(model)

    async def list_all(self) -> list[BlockedDomain]:
        result = await self._session.execute(
            select(BlockedDomainModel).order_by(BlockedDomainModel.domain.asc())
        )
        return [BlockedDomain.model_validate(model) for model in result.scalars().all()]
