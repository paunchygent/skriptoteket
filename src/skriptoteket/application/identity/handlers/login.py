from __future__ import annotations

from datetime import timedelta

from skriptoteket.application.identity.authentication import authenticate_local_user
from skriptoteket.application.identity.commands import LoginCommand, LoginResult
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Session
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    LoginHandlerProtocol,
    PasswordHasherProtocol,
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
        sessions: SessionRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._users = users
        self._sessions = sessions
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator
        self._token_generator = token_generator

    async def handle(self, command: LoginCommand) -> LoginResult:
        user = await authenticate_local_user(
            users=self._users,
            password_hasher=self._password_hasher,
            email=command.email,
            password=command.password,
        )

        now = self._clock.now()
        session = Session(
            id=self._id_generator.new_uuid(),
            user_id=user.id,
            csrf_token=self._token_generator.new_token(),
            created_at=now,
            expires_at=now + timedelta(seconds=self._settings.SESSION_TTL_SECONDS),
            revoked_at=None,
        )

        async with self._uow:
            await self._sessions.create(session=session)

        return LoginResult(
            session_id=session.id,
            csrf_token=session.csrf_token,
            user=user,
        )
