"""Password-reset execution handler.

Purpose:
  Validate a password-reset token, set a new password hash, clear lockout
  state, and invalidate pending reset tokens for the affected local user.
"""

from __future__ import annotations

from typing import Protocol

from skriptoteket.application.identity.commands import ResetPasswordCommand, ResetPasswordResult
from skriptoteket.application.identity.password_validation import validate_password_strength
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider
from skriptoteket.domain.identity.password_reset import hash_password_reset_token
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.password_reset import PasswordResetTokenRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ResetPasswordHandlerProtocol(Protocol):
    """Protocol for executing password resets."""

    async def handle(self, command: ResetPasswordCommand) -> ResetPasswordResult: ...


class ResetPasswordHandler(ResetPasswordHandlerProtocol):
    """Reset a password for a valid local account token."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        password_reset_tokens: PasswordResetTokenRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._password_reset_tokens = password_reset_tokens
        self._password_hasher = password_hasher
        self._clock = clock

    async def handle(self, command: ResetPasswordCommand) -> ResetPasswordResult:
        token_hash = hash_password_reset_token(token=command.token)

        async with self._uow:
            token_record = await self._password_reset_tokens.get_by_token_hash(
                token_hash=token_hash
            )
            if token_record is None or token_record.is_used():
                raise DomainError(
                    code=ErrorCode.INVALID_PASSWORD_RESET_TOKEN,
                    message="Ogiltig återställningslänk",
                )

            now = self._clock.now()
            if token_record.is_expired(now):
                raise DomainError(
                    code=ErrorCode.PASSWORD_RESET_TOKEN_EXPIRED,
                    message="Återställningslänken har gått ut",
                )

            user = await self._users.get_by_id(token_record.user_id)
            if user is None or user.auth_provider is not AuthProvider.LOCAL:
                raise DomainError(
                    code=ErrorCode.INVALID_PASSWORD_RESET_TOKEN,
                    message="Ogiltig återställningslänk",
                )

            validate_password_strength(password=command.new_password)

            updated_user = user.model_copy(
                update={
                    "failed_login_attempts": 0,
                    "locked_until": None,
                    "last_failed_login_at": None,
                    "updated_at": now,
                }
            )
            await self._users.update(user=updated_user)
            await self._users.update_password_hash(
                user_id=user.id,
                password_hash=self._password_hasher.hash(password=command.new_password),
                updated_at=now,
            )
            await self._password_reset_tokens.mark_used(token_id=token_record.id, used_at=now)
            await self._password_reset_tokens.invalidate_pending_for_user(
                user_id=user.id,
                used_at=now,
            )

        return ResetPasswordResult()
