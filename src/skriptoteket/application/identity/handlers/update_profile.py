from __future__ import annotations

from skriptoteket.application.identity.commands import UpdateProfileCommand, UpdateProfileResult
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UpdateProfileHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

SUPPORTED_LOCALES = {"sv-SE", "en-US"}


class UpdateProfileHandler(UpdateProfileHandlerProtocol):
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

    async def handle(self, command: UpdateProfileCommand) -> UpdateProfileResult:
        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            profile = await self._profiles.get_by_user_id(user_id=command.user_id)
            if profile is None:
                raise not_found("UserProfile", str(command.user_id))

            updates: dict[str, object] = {}

            if command.first_name is not None:
                first_name = command.first_name.strip()
                if not first_name:
                    raise DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Förnamn kan inte vara tomt",
                    )
                if len(first_name) > 100:
                    raise DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Förnamn får vara max 100 tecken",
                    )
                updates["first_name"] = first_name

            if command.last_name is not None:
                last_name = command.last_name.strip()
                if not last_name:
                    raise DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Efternamn kan inte vara tomt",
                    )
                if len(last_name) > 100:
                    raise DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Efternamn får vara max 100 tecken",
                    )
                updates["last_name"] = last_name

            if command.display_name is not None:
                display_name = command.display_name.strip()
                if display_name and len(display_name) > 100:
                    raise DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Visningsnamn får vara max 100 tecken",
                    )
                updates["display_name"] = display_name or None

            if command.locale is not None:
                if command.locale not in SUPPORTED_LOCALES:
                    raise DomainError(
                        code=ErrorCode.VALIDATION_ERROR,
                        message="Ogiltigt språkval",
                        details={"supported": sorted(SUPPORTED_LOCALES)},
                    )
                updates["locale"] = command.locale

            now = self._clock.now()
            updates["updated_at"] = now

            updated_profile = profile.model_copy(update=updates)
            saved_profile = await self._profiles.update(profile=updated_profile)

        return UpdateProfileResult(user=user, profile=saved_profile)
