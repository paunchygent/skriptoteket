"""Password reset token domain model and deterministic token hashing helpers.

Purpose:
  Represent password-reset tokens without exposing plaintext tokens at rest and
  keep reset-token validity checks framework-agnostic.

Relationships:
  - Consumed by password-reset handlers and repository protocols.
  - Mapped from SQLAlchemy models in `skriptoteket.infrastructure.db.models`.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


def hash_password_reset_token(*, token: str) -> str:
    """Hash a presented reset token into the persisted lookup value."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PasswordResetToken(BaseModel):
    """Domain model for password-reset tokens stored hashed at rest."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime

    def is_expired(self, now: datetime) -> bool:
        """Return whether the token has expired."""
        return now >= self.expires_at

    def is_used(self) -> bool:
        """Return whether the token has already been consumed or invalidated."""
        return self.used_at is not None

    def is_valid(self, now: datetime) -> bool:
        """Return whether the token is still usable."""
        return not self.is_used() and not self.is_expired(now)
