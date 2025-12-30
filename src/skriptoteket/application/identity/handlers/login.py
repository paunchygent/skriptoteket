from __future__ import annotations

from datetime import timedelta

from skriptoteket.application.identity.commands import LoginCommand, LoginResult
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.lockout import (
    is_locked_out,
    record_failed_attempt,
    reset_failed_attempts,
)
from skriptoteket.domain.identity.login_events import LoginEvent, LoginEventStatus
from skriptoteket.domain.identity.models import AuthProvider, Session, User
from skriptoteket.observability.metrics import get_metrics
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    LoginHandlerProtocol,
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.login_events import LoginEventRepositoryProtocol
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class LoginHandler(LoginHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        sessions: SessionRepositoryProtocol,
        login_events: LoginEventRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._sessions = sessions
        self._login_events = login_events
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator

    async def handle(self, command: LoginCommand) -> LoginResult:
        metrics = get_metrics()
        error_to_raise: DomainError | None = None
        result: LoginResult | None = None

        async with self._uow:
            normalized_email = command.email.strip().lower()
            user_auth = await self._users.get_auth_by_email(normalized_email)
            user: User | None = user_auth.user if user_auth else None
            auth_provider = user.auth_provider if user else command.auth_provider
            now = self._clock.now()
            event_user_id = user.id if user else None

            try:
                if not user_auth or not user_auth.user.is_active:
                    raise DomainError(
                        code=ErrorCode.INVALID_CREDENTIALS,
                        message="Invalid credentials",
                    )

                user = user_auth.user
                event_user_id = user.id

                if user.auth_provider is not AuthProvider.LOCAL:
                    raise DomainError(
                        code=ErrorCode.INVALID_CREDENTIALS,
                        message="Invalid credentials",
                    )

                if not user_auth.password_hash:
                    raise DomainError(
                        code=ErrorCode.INVALID_CREDENTIALS,
                        message="Invalid credentials",
                    )

                if is_locked_out(user=user, now=now):
                    retry_after_seconds = 0
                    if user.locked_until is not None:
                        retry_after_seconds = max(
                            0,
                            int((user.locked_until - now).total_seconds()),
                        )
                    raise DomainError(
                        code=ErrorCode.ACCOUNT_LOCKED,
                        message="Kontot är låst. Försök igen om 15 minuter.",
                        details={"retry_after_seconds": retry_after_seconds},
                    )

                if not self._password_hasher.verify(
                    password=command.password,
                    password_hash=user_auth.password_hash,
                ):
                    updated_user = record_failed_attempt(user=user, now=now)
                    await self._users.update(user=updated_user)
                    event_user_id = updated_user.id
                    if updated_user.locked_until is not None:
                        retry_after_seconds = max(
                            0,
                            int((updated_user.locked_until - now).total_seconds()),
                        )
                        raise DomainError(
                            code=ErrorCode.ACCOUNT_LOCKED,
                            message="Kontot är låst. Försök igen om 15 minuter.",
                            details={"retry_after_seconds": retry_after_seconds},
                        )
                    raise DomainError(
                        code=ErrorCode.INVALID_CREDENTIALS,
                        message="Invalid credentials",
                    )

                # Check email verification before allowing login
                if not user.email_verified:
                    raise DomainError(
                        code=ErrorCode.EMAIL_NOT_VERIFIED,
                        message="Verifiera din e-postadress innan du loggar in",
                    )

                updated_user = reset_failed_attempts(user=user, now=now)
                await self._users.update(user=updated_user)
                event_user_id = updated_user.id

                session = Session(
                    id=self._id_generator.new_uuid(),
                    user_id=updated_user.id,
                    csrf_token=self._token_generator.new_token(),
                    created_at=now,
                    expires_at=now + timedelta(seconds=self._settings.SESSION_TTL_SECONDS),
                    revoked_at=None,
                )

                await self._sessions.create(session=session)

                profile = await self._profiles.get_by_user_id(user_id=updated_user.id)
                result = LoginResult(
                    session_id=session.id,
                    csrf_token=session.csrf_token,
                    user=updated_user,
                    profile=profile,
                )
                status = LoginEventStatus.SUCCESS
                failure_code: str | None = None
            except DomainError as exc:
                error_to_raise = exc
                status = LoginEventStatus.FAILURE
                failure_code = exc.code.value

            event = LoginEvent(
                id=self._id_generator.new_uuid(),
                user_id=event_user_id,
                status=status,
                failure_code=failure_code,
                ip_address=command.ip_address,
                user_agent=command.user_agent,
                auth_provider=auth_provider,
                correlation_id=command.correlation_id,
                geo_country_code=None,
                geo_region=None,
                geo_city=None,
                geo_latitude=None,
                geo_longitude=None,
                created_at=now,
            )
            await self._login_events.create(event=event)

        if error_to_raise is not None:
            metrics["logins_total"].labels(status="failure").inc()
            raise error_to_raise

        metrics["logins_total"].labels(status="success").inc()
        if result is None:
            raise DomainError(code=ErrorCode.INTERNAL_ERROR, message="Login failed")
        return result
