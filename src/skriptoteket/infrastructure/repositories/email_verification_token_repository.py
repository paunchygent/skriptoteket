"""PostgreSQL repository for email verification tokens."""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.email_verification import EmailVerificationToken
from skriptoteket.infrastructure.db.models.email_verification_token import (
    EmailVerificationTokenModel,
)
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol


class PostgreSQLEmailVerificationTokenRepository(EmailVerificationTokenRepositoryProtocol):
    """PostgreSQL repository for email verification tokens.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, token: EmailVerificationToken) -> EmailVerificationToken:
        """Create a new verification token."""
        model = EmailVerificationTokenModel(
            id=token.id,
            user_id=token.user_id,
            token=token.token,
            expires_at=token.expires_at,
            verified_at=token.verified_at,
            created_at=token.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return EmailVerificationToken.model_validate(model)

    async def get_by_token(self, token: str) -> EmailVerificationToken | None:
        """Get token by its value."""
        stmt = select(EmailVerificationTokenModel).where(EmailVerificationTokenModel.token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return EmailVerificationToken.model_validate(model) if model else None

    async def get_latest_by_user_id(self, user_id: UUID) -> EmailVerificationToken | None:
        """Get the latest (most recent) token for a user."""
        stmt = (
            select(EmailVerificationTokenModel)
            .where(EmailVerificationTokenModel.user_id == user_id)
            .order_by(EmailVerificationTokenModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return EmailVerificationToken.model_validate(model) if model else None

    async def mark_verified(self, *, token_id: UUID, verified_at: datetime) -> None:
        """Mark a token as verified."""
        stmt = (
            update(EmailVerificationTokenModel)
            .where(EmailVerificationTokenModel.id == token_id)
            .values(verified_at=verified_at)
        )
        await self._session.execute(stmt)

    async def delete_expired(self, *, cutoff: datetime) -> int:
        """Delete expired tokens. Returns count deleted."""
        stmt = delete(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.expires_at < cutoff
        )
        result = await self._session.execute(stmt)
        return int(cast(CursorResult[object], result).rowcount or 0)

    async def invalidate_all_for_user(self, *, user_id: UUID) -> int:
        """Delete all pending tokens for a user."""
        stmt = delete(EmailVerificationTokenModel).where(
            EmailVerificationTokenModel.user_id == user_id,
            EmailVerificationTokenModel.verified_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return int(cast(CursorResult[object], result).rowcount or 0)
