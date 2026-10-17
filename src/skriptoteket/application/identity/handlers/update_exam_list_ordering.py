"""Persist the teacher's saved-exam ordering across browsers."""

from skriptoteket.application.identity.commands import (
    UpdateExamListOrderingCommand,
    UpdateExamListOrderingResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UpdateExamListOrderingHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class UpdateExamListOrderingHandler(UpdateExamListOrderingHandlerProtocol):
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

    async def handle(self, command: UpdateExamListOrderingCommand) -> UpdateExamListOrderingResult:
        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))
            profile = await self._profiles.get_by_user_id(user_id=command.user_id)
            if profile is None:
                raise not_found("UserProfile", str(command.user_id))
            saved = await self._profiles.update(
                profile=profile.model_copy(
                    update={
                        "exam_list_ordering": command.ordering,
                        "updated_at": self._clock.now(),
                    }
                ),
                fields=frozenset({"exam_list_ordering", "updated_at"}),
            )
        return UpdateExamListOrderingResult(user=user, profile=saved)
