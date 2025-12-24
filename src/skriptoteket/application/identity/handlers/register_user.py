from __future__ import annotations

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
from skriptoteket.domain.identity.models import Role, Session, UserProfile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    RegisterUserHandlerProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class RegisterUserHandler(RegisterUserHandlerProtocol):
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

            session = Session(
                id=self._id_generator.new_uuid(),
                user_id=result.user.id,
                csrf_token=self._token_generator.new_token(),
                created_at=now,
                expires_at=now + timedelta(seconds=self._settings.SESSION_TTL_SECONDS),
                revoked_at=None,
            )
            await self._sessions.create(session=session)

        return RegisterUserResult(
            session_id=session.id,
            csrf_token=session.csrf_token,
            user=result.user,
            profile=created_profile,
        )
