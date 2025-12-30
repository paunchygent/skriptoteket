"""Handler for email verification."""

from __future__ import annotations

from typing import Protocol

from skriptoteket.application.identity.commands import VerifyEmailCommand, VerifyEmailResult
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class VerifyEmailHandlerProtocol(Protocol):
    """Protocol for email verification handler."""

    async def handle(self, command: VerifyEmailCommand) -> VerifyEmailResult:
        """Verify email with token."""
        ...


class VerifyEmailHandler(VerifyEmailHandlerProtocol):
    """Handler for verifying email addresses."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        verification_tokens: EmailVerificationTokenRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._verification_tokens = verification_tokens
        self._clock = clock

    async def handle(self, command: VerifyEmailCommand) -> VerifyEmailResult:
        """Verify email with token."""
        async with self._uow:
            token_record = await self._verification_tokens.get_by_token(command.token)

            if token_record is None:
                raise DomainError(
                    code=ErrorCode.INVALID_VERIFICATION_TOKEN,
                    message="Ogiltig verifieringslänk",
                )

            now = self._clock.now()

            if token_record.is_used():
                raise DomainError(
                    code=ErrorCode.INVALID_VERIFICATION_TOKEN,
                    message="Verifieringslänken har redan använts",
                )

            if token_record.is_expired(now):
                raise DomainError(
                    code=ErrorCode.VERIFICATION_TOKEN_EXPIRED,
                    message="Verifieringslänken har gått ut, begär en ny",
                )

            # Mark token as used
            await self._verification_tokens.mark_verified(
                token_id=token_record.id,
                verified_at=now,
            )

            # Update user's email_verified flag
            user = await self._users.get_by_id(token_record.user_id)
            if user is None:
                raise DomainError(
                    code=ErrorCode.USER_NOT_FOUND,
                    message="Användaren finns inte",
                )

            updated_user = user.model_copy(update={"email_verified": True, "updated_at": now})
            await self._users.update(user=updated_user)

            # Clean up other pending tokens for this user
            await self._verification_tokens.invalidate_all_for_user(user_id=user.id)

        return VerifyEmailResult(user=updated_user)
