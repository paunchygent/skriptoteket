from __future__ import annotations

from skriptoteket.application.identity.commands import CreateLocalUserCommand, CreateLocalUserResult
from skriptoteket.application.identity.local_user_creation import create_local_user
from skriptoteket.config import Settings
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
        async with self._uow:
            return await create_local_user(
                users=self._users,
                password_hasher=self._password_hasher,
                clock=self._clock,
                id_generator=self._id_generator,
                command=command,
            )
