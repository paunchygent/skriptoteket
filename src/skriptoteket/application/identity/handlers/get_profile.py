from __future__ import annotations

from skriptoteket.application.identity.commands import GetProfileCommand, GetProfileResult
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.identity import (
    GetProfileHandlerProtocol,
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class GetProfileHandler(GetProfileHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._profiles = profiles

    async def handle(self, command: GetProfileCommand) -> GetProfileResult:
        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            profile = await self._profiles.get_by_user_id(user_id=command.user_id)
            if profile is None:
                raise not_found("UserProfile", str(command.user_id))

        return GetProfileResult(user=user, profile=profile)
