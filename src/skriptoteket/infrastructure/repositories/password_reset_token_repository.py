"""PostgreSQL repository for password-reset tokens.

Purpose:
  Persist password-reset tokens hashed at rest and enforce lookup/update
  operations without owning transaction boundaries.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.password_reset import PasswordResetToken
from skriptoteket.infrastructure.db.models.password_reset_token import PasswordResetTokenModel
from skriptoteket.protocols.password_reset import PasswordResetTokenRepositoryProtocol


class PostgreSQLPasswordResetTokenRepository(PasswordResetTokenRepositoryProtocol):
    """Request-scoped password-reset token repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, token: PasswordResetToken) -> PasswordResetToken:
        model = PasswordResetTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            used_at=token.used_at,
            created_at=token.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return PasswordResetToken.model_validate(model)

    async def get_by_token_hash(self, *, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return PasswordResetToken.model_validate(model) if model else None

    async def get_latest_by_user_id(self, *, user_id: UUID) -> PasswordResetToken | None:
        stmt = (
            select(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.user_id == user_id)
            .order_by(PasswordResetTokenModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return PasswordResetToken.model_validate(model) if model else None

    async def mark_used(self, *, token_id: UUID, used_at: datetime) -> None:
        await self._session.execute(
            update(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.id == token_id)
            .values(used_at=used_at)
        )

    async def invalidate_pending_for_user(self, *, user_id: UUID, used_at: datetime) -> int:
        result = await self._session.execute(
            update(PasswordResetTokenModel)
            .where(
                PasswordResetTokenModel.user_id == user_id,
                PasswordResetTokenModel.used_at.is_(None),
            )
            .values(used_at=used_at)
        )
        return int(cast(CursorResult[object], result).rowcount or 0)
