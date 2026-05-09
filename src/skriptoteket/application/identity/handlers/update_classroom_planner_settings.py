"""Profile-backed classroom planner smart preference update handler.

Purpose:
    Persist authenticated teachers' classroom planner Smart choices in their
    app-local profile so new drafts seed from the same preference across
    browsers and devices.

Relationships:
    - Invoked by `/api/v1/profile/classroom-planner-settings`.
    - Read by classroom planner draft creation routes before creating a new
      authenticated draft.
"""

from __future__ import annotations

from skriptoteket.application.identity.commands import (
    UpdateClassroomPlannerSettingsCommand,
    UpdateClassroomPlannerSettingsResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UpdateClassroomPlannerSettingsHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class UpdateClassroomPlannerSettingsHandler(UpdateClassroomPlannerSettingsHandlerProtocol):
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

    async def handle(
        self,
        command: UpdateClassroomPlannerSettingsCommand,
    ) -> UpdateClassroomPlannerSettingsResult:
        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            profile = await self._profiles.get_by_user_id(user_id=command.user_id)
            if profile is None:
                raise not_found("UserProfile", str(command.user_id))

            update: dict[str, object] = {"updated_at": self._clock.now()}
            if command.smart_enabled is not None:
                update["classroom_planner_smart_enabled"] = command.smart_enabled
            if command.use_history is not None:
                update["classroom_planner_use_history"] = command.use_history
            if command.grouping_seating_distance_enabled is not None:
                update["classroom_planner_grouping_seating_distance_enabled"] = (
                    command.grouping_seating_distance_enabled
                )

            saved_profile = await self._profiles.update(profile=profile.model_copy(update=update))

        return UpdateClassroomPlannerSettingsResult(user=user, profile=saved_profile)
