from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import Session
from skriptoteket.infrastructure.db.models.session import SessionModel
from skriptoteket.protocols.identity import SessionRepositoryProtocol


class PostgreSQLSessionRepository(SessionRepositoryProtocol):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, session: Session) -> None:
        model = SessionModel(
            id=session.id,
            user_id=session.user_id,
            csrf_token=session.csrf_token,
            expires_at=session.expires_at,
            revoked_at=session.revoked_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, session_id: UUID) -> Session | None:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return Session.model_validate(model) if model else None

    async def revoke(self, *, session_id: UUID) -> None:
        await self._session.execute(
            update(SessionModel).where(SessionModel.id == session_id).values(revoked_at=func.now())
        )
