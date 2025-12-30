"""Handler for resending email verification."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Protocol

from skriptoteket.application.identity.commands import (
    ResendVerificationCommand,
    ResendVerificationResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.email_verification import EmailVerificationToken
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email import EmailSenderProtocol, EmailTemplateRendererProtocol
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import ProfileRepositoryProtocol, UserRepositoryProtocol
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = logging.getLogger(__name__)

# Rate limit: minimum seconds between resend requests
RESEND_RATE_LIMIT_SECONDS = 60


class ResendVerificationHandlerProtocol(Protocol):
    """Protocol for resend verification handler."""

    async def handle(self, command: ResendVerificationCommand) -> ResendVerificationResult:
        """Resend verification email."""
        ...


class ResendVerificationHandler(ResendVerificationHandlerProtocol):
    """Handler for resending verification emails."""

    def __init__(
        self,
        *,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        verification_tokens: EmailVerificationTokenRepositoryProtocol,
        email_sender: EmailSenderProtocol,
        email_renderer: EmailTemplateRendererProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._verification_tokens = verification_tokens
        self._email_sender = email_sender
        self._email_renderer = email_renderer
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator

    async def handle(self, command: ResendVerificationCommand) -> ResendVerificationResult:
        """Resend verification email.

        Always returns success message for security (don't reveal if email exists).
        """
        normalized_email = command.email.strip().lower()

        async with self._uow:
            user_auth = await self._users.get_auth_by_email(normalized_email)

            if user_auth is None or user_auth.user.email_verified:
                # Don't reveal whether user exists or is already verified
                return ResendVerificationResult()

            user = user_auth.user
            profile = await self._profiles.get_by_user_id(user_id=user.id)
            first_name = profile.first_name if profile else user.email

            # Check rate limiting: don't create new token if recent one exists
            existing = await self._verification_tokens.get_latest_by_user_id(user.id)
            now = self._clock.now()

            if existing and (now - existing.created_at).total_seconds() < RESEND_RATE_LIMIT_SECONDS:
                # Rate limited - silently return success
                return ResendVerificationResult()

            # Create new token
            token = EmailVerificationToken(
                id=self._id_generator.new_uuid(),
                user_id=user.id,
                token=self._token_generator.new_token(),
                expires_at=now + timedelta(hours=self._settings.EMAIL_VERIFICATION_TTL_HOURS),
                verified_at=None,
                created_at=now,
            )
            await self._verification_tokens.create(token=token)

        # Send email outside transaction
        await self._send_verification_email(
            email=user.email,
            first_name=first_name or user.email,
            token=token.token,
        )

        return ResendVerificationResult()

    async def _send_verification_email(
        self,
        *,
        email: str,
        first_name: str,
        token: str,
    ) -> None:
        """Send verification email."""
        try:
            verification_url = (
                f"{self._settings.EMAIL_VERIFICATION_BASE_URL}/verify-email?token={token}"
            )
            message = self._email_renderer.render(
                template_name="verify_email.html",
                context={
                    "to_email": email,
                    "first_name": first_name,
                    "verification_url": verification_url,
                    "expiry_hours": self._settings.EMAIL_VERIFICATION_TTL_HOURS,
                    "base_url": self._settings.EMAIL_VERIFICATION_BASE_URL,
                },
            )
            await self._email_sender.send(message=message)
        except Exception:
            logger.exception("Failed to send verification email", extra={"email": email})
