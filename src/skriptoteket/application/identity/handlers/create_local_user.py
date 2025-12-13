from __future__ import annotations

from skriptoteket.application.identity.commands import CreateLocalUserCommand, CreateLocalUserResult
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    CreateLocalUserHandlerProtocol,
    PasswordHasherProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class CreateLocalUserHandler(CreateLocalUserHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._settings = settings
        self._uow = uow
        self._users = users
        self._password_hasher = password_hasher
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, command: CreateLocalUserCommand) -> CreateLocalUserResult:
        email = command.email.strip().lower()
        if await self._users.get_auth_by_email(email):
            raise DomainError(code=ErrorCode.DUPLICATE_ENTRY, message="Email already exists")

        now = self._clock.now()
        user = User(
            id=self._id_generator.new_uuid(),
            email=email,
            role=command.role,
            auth_provider=AuthProvider.LOCAL,
            external_id=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        password_hash = self._password_hasher.hash(password=command.password)

        async with self._uow:
            created = await self._users.create(user=user, password_hash=password_hash)

        return CreateLocalUserResult(user=created)
