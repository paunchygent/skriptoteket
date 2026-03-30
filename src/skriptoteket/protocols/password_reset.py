"""Password-reset repository and throttling protocols.

Purpose:
  Keep password-reset persistence and request-cooldown behavior protocol-first
  so handlers depend on stable seams instead of concrete storage choices.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.identity.password_reset import PasswordResetToken


class PasswordResetTokenRepositoryProtocol(Protocol):
    """Repository protocol for password-reset tokens."""

    async def create(self, *, token: PasswordResetToken) -> PasswordResetToken: ...
    async def get_by_token_hash(self, *, token_hash: str) -> PasswordResetToken | None: ...
    async def get_latest_by_user_id(self, *, user_id: UUID) -> PasswordResetToken | None: ...
    async def mark_used(self, *, token_id: UUID, used_at: datetime) -> None: ...
    async def invalidate_pending_for_user(self, *, user_id: UUID, used_at: datetime) -> int: ...


class PasswordResetRequestThrottleProtocol(Protocol):
    """Cooldown protocol for anonymous forgot-password requests."""

    def is_rate_limited(self, *, normalized_email: str, now: datetime) -> bool: ...
    def record_request(self, *, normalized_email: str, now: datetime) -> None: ...
