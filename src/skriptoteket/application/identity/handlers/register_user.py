"""User self-registration handler.

Purpose:
  Validate registration input, enforce the school-domain allowlist, create the
  local user/profile pair, and send the verification email within one unit of
  work so failures roll back cleanly.

Relationships:
  - Depends on protocol-first repositories and services from the identity layer.
  - Reuses local user creation and password validation helpers.
  - Calls the registration-domain validator before any user is persisted.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from skriptoteket.application.identity.auth_link_continuation import append_auth_link_continuation
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
from skriptoteket.domain.identity.models import Role, User, UserProfile
from skriptoteket.domain.identity.role_guards import has_at_least_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.email import EmailSenderProtocol, EmailTemplateRendererProtocol
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    DomainValidatorProtocol,
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    RegisterUserHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = logging.getLogger(__name__)

EMAIL_SEND_MAX_ATTEMPTS = 3
EMAIL_SEND_BACKOFF_BASE_SECONDS = 0.5


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
        sleeper: SleeperProtocol,
        domain_validator: DomainValidatorProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
        favorites: FavoritesRepositoryProtocol | None = None,
        curated_apps: CuratedAppRegistryProtocol | None = None,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._verification_tokens = verification_tokens
        self._email_sender = email_sender
        self._email_renderer = email_renderer
        self._sleeper = sleeper
        self._domain_validator = domain_validator
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator
        self._favorites = favorites
        self._curated_apps = curated_apps

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
        await self._domain_validator.validate_registration_email(command.email)

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
            allow_remote_fallback = (
                True
                if self._settings.AI_REMOTE_PROVIDERS_ENABLED
                and self._settings.AI_DEFAULT_ALLOW_REMOTE_FALLBACK
                else None
            )
            profile = UserProfile(
                user_id=result.user.id,
                first_name=first_name,
                last_name=last_name,
                display_name=None,
                allow_remote_fallback=allow_remote_fallback,
                inline_completion_provider=None,
                locale="sv-SE",
                created_at=now,
                updated_at=now,
            )
            created_profile = await self._profiles.create(profile=profile)
            await self._add_default_curated_app_favorites(user=result.user)

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

            await self._send_verification_email_with_retry(
                email=result.user.email,
                first_name=first_name,
                token=verification_token.token,
                next_path=command.next_path,
                classroom_planner_entry_origin=command.classroom_planner_entry_origin,
            )

        return RegisterUserResult(
            user=result.user,
            profile=created_profile,
            verification_email_sent=True,
        )

    async def _add_default_curated_app_favorites(self, *, user: User) -> None:
        """Persist default curated-app favorites for newly registered users."""
        if self._favorites is None or self._curated_apps is None:
            return

        for app in self._curated_apps.list_all():
            if not app.default_favorite or not has_at_least_role(user=user, role=app.min_role):
                continue
            await self._favorites.add_app(user_id=user.id, app_id=app.app_id)

    async def _send_verification_email_with_retry(
        self,
        *,
        email: str,
        first_name: str,
        token: str,
        next_path: str | None,
        classroom_planner_entry_origin: str | None,
    ) -> None:
        """Send verification email with retry + exponential backoff.

        Must be called inside the registration transaction so failures roll back user creation.
        """
        base_url = self._settings.EMAIL_VERIFICATION_BASE_URL
        verification_url = append_auth_link_continuation(
            base_url=base_url,
            path="/verify-email",
            token_name="token",
            token_value=token,
            next_path=next_path,
            classroom_planner_entry_origin=classroom_planner_entry_origin,
        )
        message = self._email_renderer.render(
            template_name="verify_email.html",
            context={
                "to_email": email,
                "first_name": first_name,
                "verification_url": verification_url,
                "expiry_hours": self._settings.EMAIL_VERIFICATION_TTL_HOURS,
                "base_url": base_url,
            },
        )

        last_error: DomainError | None = None

        for attempt in range(1, EMAIL_SEND_MAX_ATTEMPTS + 1):
            try:
                await self._email_sender.send(message=message)
                return
            except DomainError as exc:
                last_error = exc
                is_retryable = bool(exc.details.get("retryable"))
                if not is_retryable or attempt >= EMAIL_SEND_MAX_ATTEMPTS:
                    logger.warning(
                        "Registration failed: could not send verification email",
                        extra={
                            "attempt": attempt,
                            "retryable": is_retryable,
                            "error_code": exc.code.value,
                        },
                    )
                    raise DomainError(
                        code=ErrorCode.EMAIL_SEND_FAILED,
                        message="Kunde inte skicka verifieringsmail. Försök igen.",
                        details={
                            "retryable": False,
                            "attempts": attempt,
                            "last_error_code": exc.code.value,
                        },
                    ) from exc

                delay_seconds = EMAIL_SEND_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                logger.info(
                    "Transient email failure; retrying verification email send",
                    extra={
                        "attempt": attempt,
                        "retry_in_seconds": delay_seconds,
                        "error_code": exc.code.value,
                    },
                )
                await self._sleeper.sleep(delay_seconds)
            except Exception as exc:  # pragma: no cover
                logger.exception(
                    "Registration failed: unexpected error while sending verification email",
                    extra={"attempt": attempt},
                )
                raise DomainError(
                    code=ErrorCode.EMAIL_SEND_FAILED,
                    message="Kunde inte skicka verifieringsmail. Försök igen.",
                    details={
                        "retryable": False,
                        "attempts": attempt,
                        "last_error_type": type(exc).__name__,
                    },
                ) from exc

        # Defensive: loop should always return or raise.
        raise DomainError(
            code=ErrorCode.EMAIL_SEND_FAILED,
            message="Kunde inte skicka verifieringsmail. Försök igen.",
            details={
                "retryable": False,
                "attempts": EMAIL_SEND_MAX_ATTEMPTS,
                "last_error_code": last_error.code.value if last_error else None,
            },
        )
