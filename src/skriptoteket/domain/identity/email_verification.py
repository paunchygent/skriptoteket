"""Email verification token domain model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmailVerificationToken(BaseModel):
    """Domain model for email verification tokens."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    user_id: UUID
    token: str
    expires_at: datetime
    verified_at: datetime | None = None
    created_at: datetime

    def is_expired(self, now: datetime) -> bool:
        """Check if the token has expired."""
        return now >= self.expires_at

    def is_used(self) -> bool:
        """Check if the token has been used."""
        return self.verified_at is not None

    def is_valid(self, now: datetime) -> bool:
        """Check if the token is valid (not expired and not used)."""
        return not self.is_expired(now) and not self.is_used()
