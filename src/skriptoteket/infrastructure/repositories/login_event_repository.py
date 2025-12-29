from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.login_events import LoginEvent
from skriptoteket.infrastructure.db.models.login_event import LoginEventModel
from skriptoteket.protocols.login_events import LoginEventRepositoryProtocol


class PostgreSQLLoginEventRepository(LoginEventRepositoryProtocol):
    """PostgreSQL repository for login events.

    Uses a request-scoped AsyncSession; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, event: LoginEvent) -> LoginEvent:
        model = LoginEventModel(
            id=event.id,
            user_id=event.user_id,
            status=event.status.value,
            failure_code=event.failure_code,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            auth_provider=event.auth_provider.value,
            correlation_id=event.correlation_id,
            geo_country_code=event.geo_country_code,
            geo_region=event.geo_region,
            geo_city=event.geo_city,
            geo_latitude=event.geo_latitude,
            geo_longitude=event.geo_longitude,
            created_at=event.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return LoginEvent.model_validate(model)

    async def list_by_user(
        self, *, user_id: UUID, limit: int, since: datetime | None = None
    ) -> list[LoginEvent]:
        stmt = select(LoginEventModel).where(LoginEventModel.user_id == user_id)
        if since is not None:
            stmt = stmt.where(LoginEventModel.created_at >= since)
        stmt = stmt.order_by(LoginEventModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [LoginEvent.model_validate(model) for model in result.scalars().all()]

    async def delete_expired(self, *, cutoff: datetime) -> int:
        stmt = delete(LoginEventModel).where(LoginEventModel.created_at < cutoff)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(cast(CursorResult[object], result).rowcount or 0)
