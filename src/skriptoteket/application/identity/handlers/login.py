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
from skriptoteket.domain.identity.models import AuthProvider, Session
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    LoginHandlerProtocol,
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
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
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator

    async def handle(self, command: LoginCommand) -> LoginResult:
        async with self._uow:
            normalized_email = command.email.strip().lower()
            user_auth = await self._users.get_auth_by_email(normalized_email)
            if not user_auth or not user_auth.user.is_active:
                raise DomainError(code=ErrorCode.INVALID_CREDENTIALS, message="Invalid credentials")

            user = user_auth.user

            if user.auth_provider is not AuthProvider.LOCAL:
                raise DomainError(code=ErrorCode.INVALID_CREDENTIALS, message="Invalid credentials")

            if not user_auth.password_hash:
                raise DomainError(code=ErrorCode.INVALID_CREDENTIALS, message="Invalid credentials")

            now = self._clock.now()
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
                raise DomainError(code=ErrorCode.INVALID_CREDENTIALS, message="Invalid credentials")

            updated_user = reset_failed_attempts(user=user, now=now)
            await self._users.update(user=updated_user)

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

        return LoginResult(
            session_id=session.id,
            csrf_token=session.csrf_token,
            user=updated_user,
            profile=profile,
        )
