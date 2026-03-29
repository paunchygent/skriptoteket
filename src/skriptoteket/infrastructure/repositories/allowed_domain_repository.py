"""PostgreSQL repository for allowed registration domains.

Purpose:
  Persist and query normalized allowlist root domains without letting repository
  code own transaction boundaries.

Relationships:
  - Uses `AllowedDomainModel` for SQLAlchemy persistence.
  - Implements `AllowedDomainRepositoryProtocol`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AllowedDomain
from skriptoteket.infrastructure.db.models.allowed_domain import AllowedDomainModel
from skriptoteket.protocols.identity import AllowedDomainRepositoryProtocol


class PostgreSQLAllowedDomainRepository(AllowedDomainRepositoryProtocol):
    """Persist allowlist rows inside the active SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_domain(self, domain: str) -> AllowedDomain | None:
        model = await self._session.get(AllowedDomainModel, domain)
        return AllowedDomain.model_validate(model) if model else None

    async def upsert(self, *, domain: AllowedDomain) -> AllowedDomain:
        model = await self._session.get(AllowedDomainModel, domain.domain)
        if model is None:
            model = AllowedDomainModel(
                domain=domain.domain,
                org_type=domain.org_type.value,
                org_name=domain.org_name,
                source=domain.source,
                source_ref=domain.source_ref,
                is_active=domain.is_active,
                notes=domain.notes,
                created_at=domain.created_at,
                updated_at=domain.updated_at,
            )
            self._session.add(model)
        else:
            model.org_type = domain.org_type.value
            model.org_name = domain.org_name
            model.source = domain.source
            model.source_ref = domain.source_ref
            model.is_active = domain.is_active
            model.notes = domain.notes
            model.updated_at = domain.updated_at

        await self._session.flush()
        await self._session.refresh(model)
        return AllowedDomain.model_validate(model)

    async def list_all(self) -> list[AllowedDomain]:
        result = await self._session.execute(
            select(AllowedDomainModel).order_by(AllowedDomainModel.domain.asc())
        )
        return [AllowedDomain.model_validate(model) for model in result.scalars().all()]
