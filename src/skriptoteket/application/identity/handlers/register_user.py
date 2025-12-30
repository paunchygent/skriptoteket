from __future__ import annotations

import logging
from datetime import timedelta

from skriptoteket.application.identity.commands import (
    CreateLocalUserCommand,
    RegisterUserCommand,
    RegisterUserResult,
)
from skriptoteket.application.identity.local_user_creation import create_local_user
from skriptoteket.application.identity.password_validation import validate_password_strength
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.email_verification import EmailVerificationToken
from skriptoteket.domain.identity.models import Role, UserProfile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email import EmailSenderProtocol, EmailTemplateRendererProtocol
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    RegisterUserHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = logging.getLogger(__name__)


class RegisterUserHandler(RegisterUserHandlerProtocol):
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
        password_hasher: PasswordHasherProtocol,
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
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator

    async def handle(self, command: RegisterUserCommand) -> RegisterUserResult:
        first_name = command.first_name.strip()
        last_name = command.last_name.strip()

        if not first_name or not last_name:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Förnamn och efternamn måste anges",
            )

        if len(first_name) > 100 or len(last_name) > 100:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Namn får vara max 100 tecken",
            )

        validate_password_strength(password=command.password)

        async with self._uow:
            result = await create_local_user(
                users=self._users,
                password_hasher=self._password_hasher,
                clock=self._clock,
                id_generator=self._id_generator,
                command=CreateLocalUserCommand(
                    email=command.email,
                    password=command.password,
                    role=Role.USER,
                ),
                email_verified=False,
            )

            now = self._clock.now()
            profile = UserProfile(
                user_id=result.user.id,
                first_name=first_name,
                last_name=last_name,
                display_name=None,
                locale="sv-SE",
                created_at=now,
                updated_at=now,
            )
            created_profile = await self._profiles.create(profile=profile)

            # Create verification token
            verification_token = EmailVerificationToken(
                id=self._id_generator.new_uuid(),
                user_id=result.user.id,
                token=self._token_generator.new_token(),
                expires_at=now + timedelta(hours=self._settings.EMAIL_VERIFICATION_TTL_HOURS),
                verified_at=None,
                created_at=now,
            )
            await self._verification_tokens.create(token=verification_token)

        # Send verification email outside transaction
        email_sent = await self._send_verification_email(
            email=result.user.email,
            first_name=first_name,
            token=verification_token.token,
        )

        return RegisterUserResult(
            user=result.user,
            profile=created_profile,
            verification_email_sent=email_sent,
        )

    async def _send_verification_email(
        self,
        *,
        email: str,
        first_name: str,
        token: str,
    ) -> bool:
        """Send verification email. Returns True if sent successfully."""
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
            return True
        except Exception:
            logger.exception("Failed to send verification email", extra={"email": email})
            return False
