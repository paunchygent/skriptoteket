"""Anonymous password-reset request handler.

Purpose:
  Issue one-time password-reset tokens for eligible local users while preserving
  the public generic-success contract and enforcing the application-owned
  normalized-email cooldown.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Protocol

from skriptoteket.application.identity.auth_link_continuation import append_auth_link_continuation
from skriptoteket.application.identity.commands import (
    RequestPasswordResetCommand,
    RequestPasswordResetResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import AuthProvider
from skriptoteket.domain.identity.password_reset import (
    PasswordResetToken,
    hash_password_reset_token,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email import EmailSenderProtocol, EmailTemplateRendererProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.password_reset import (
    PasswordResetRequestThrottleProtocol,
    PasswordResetTokenRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = logging.getLogger(__name__)


class RequestPasswordResetHandlerProtocol(Protocol):
    """Protocol for password-reset email requests."""

    async def handle(self, command: RequestPasswordResetCommand) -> RequestPasswordResetResult: ...


class RequestPasswordResetHandler(RequestPasswordResetHandlerProtocol):
    """Issue password-reset tokens while keeping anonymous responses generic."""

    def __init__(
        self,
        *,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        password_reset_tokens: PasswordResetTokenRepositoryProtocol,
        password_reset_throttle: PasswordResetRequestThrottleProtocol,
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
        self._password_reset_tokens = password_reset_tokens
        self._password_reset_throttle = password_reset_throttle
        self._email_sender = email_sender
        self._email_renderer = email_renderer
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator

    async def handle(self, command: RequestPasswordResetCommand) -> RequestPasswordResetResult:
        normalized_email = command.email.strip().lower()
        now = self._clock.now()

        if self._password_reset_throttle.is_rate_limited(
            normalized_email=normalized_email,
            now=now,
        ):
            return RequestPasswordResetResult()

        self._password_reset_throttle.record_request(normalized_email=normalized_email, now=now)

        reset_token: str | None = None
        recipient_email: str | None = None
        first_name: str | None = None

        async with self._uow:
            user_auth = await self._users.get_auth_by_email(normalized_email)
            if user_auth is None:
                return RequestPasswordResetResult()

            user = user_auth.user
            if (
                not user.is_active
                or not user.email_verified
                or user.auth_provider is not AuthProvider.LOCAL
                or not user_auth.password_hash
            ):
                return RequestPasswordResetResult()

            await self._password_reset_tokens.invalidate_pending_for_user(
                user_id=user.id,
                used_at=now,
            )

            reset_token = self._token_generator.new_token()
            created_token = PasswordResetToken(
                id=self._id_generator.new_uuid(),
                user_id=user.id,
                token_hash=hash_password_reset_token(token=reset_token),
                expires_at=now + timedelta(hours=self._settings.PASSWORD_RESET_TTL_HOURS),
                used_at=None,
                created_at=now,
            )
            await self._password_reset_tokens.create(token=created_token)

            profile = await self._profiles.get_by_user_id(user_id=user.id)
            recipient_email = user.email
            first_name = profile.first_name if profile and profile.first_name else user.email

        if reset_token is not None and recipient_email is not None and first_name is not None:
            await self._send_reset_email(
                email=recipient_email,
                first_name=first_name,
                token=reset_token,
                next_path=command.next_path,
                classroom_planner_entry_origin=command.classroom_planner_entry_origin,
            )

        return RequestPasswordResetResult()

    async def _send_reset_email(
        self,
        *,
        email: str,
        first_name: str,
        token: str,
        next_path: str | None,
        classroom_planner_entry_origin: str | None,
    ) -> None:
        """Send the reset email without surfacing delivery failures to the public route."""
        try:
            reset_url = append_auth_link_continuation(
                base_url=self._settings.PASSWORD_RESET_BASE_URL,
                path="/reset-password",
                token_name="token",
                token_value=token,
                next_path=next_path,
                classroom_planner_entry_origin=classroom_planner_entry_origin,
            )
            message = self._email_renderer.render(
                template_name="reset_password.html",
                context={
                    "to_email": email,
                    "first_name": first_name,
                    "reset_url": reset_url,
                    "expiry_hours": self._settings.PASSWORD_RESET_TTL_HOURS,
                    "base_url": self._settings.PASSWORD_RESET_BASE_URL,
                },
            )
            await self._email_sender.send(message=message)
        except Exception:
            logger.exception("Failed to send password reset email", extra={"email": email})
