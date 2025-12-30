"""Email verification protocols."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.identity.email_verification import EmailVerificationToken


class EmailVerificationTokenRepositoryProtocol(Protocol):
    """Repository for email verification tokens."""

    async def create(self, *, token: EmailVerificationToken) -> EmailVerificationToken:
        """Create a new verification token."""
        ...

    async def get_by_token(self, token: str) -> EmailVerificationToken | None:
        """Get token by its value."""
        ...

    async def get_latest_by_user_id(self, user_id: UUID) -> EmailVerificationToken | None:
        """Get the latest (most recent) token for a user."""
        ...

    async def mark_verified(self, *, token_id: UUID, verified_at: datetime) -> None:
        """Mark a token as verified."""
        ...

    async def delete_expired(self, *, cutoff: datetime) -> int:
        """Delete expired tokens. Returns count deleted."""
        ...

    async def invalidate_all_for_user(self, *, user_id: UUID) -> int:
        """Delete all pending tokens for a user."""
        ...
