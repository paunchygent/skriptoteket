from __future__ import annotations

from skriptoteket.application.identity.commands import (
    UpdateAiSettingsCommand,
    UpdateAiSettingsResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UpdateAiSettingsHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class UpdateAiSettingsHandler(UpdateAiSettingsHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._clock = clock

    async def handle(self, command: UpdateAiSettingsCommand) -> UpdateAiSettingsResult:
        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            profile = await self._profiles.get_by_user_id(user_id=command.user_id)
            if profile is None:
                raise not_found("UserProfile", str(command.user_id))

            if command.remote_fallback_preference == "allow":
                allow_remote_fallback: bool | None = True
            elif command.remote_fallback_preference == "deny":
                allow_remote_fallback = False
            else:
                allow_remote_fallback = None

            now = self._clock.now()
            updated_profile = profile.model_copy(
                update={"allow_remote_fallback": allow_remote_fallback, "updated_at": now}
            )
            saved_profile = await self._profiles.update(profile=updated_profile)

        return UpdateAiSettingsResult(user=user, profile=saved_profile)
