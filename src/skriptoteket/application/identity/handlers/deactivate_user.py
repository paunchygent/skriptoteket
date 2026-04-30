"""Superuser-owned account deactivation handler.

Purpose:
    Provide a production identity lifecycle path for deactivating local users
    while applying deterministic share-artifact revocation first.

Relationships:
    - Invoked by the admin users API.
    - Uses the Klassrumskartan owner-share lifecycle protocol so share artifacts
      are revoked and detached in the same Unit of Work as the user update.
"""

from __future__ import annotations

from skriptoteket.application.identity.admin_users import (
    DeactivateUserCommand,
    DeactivateUserResult,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_any_role
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareOwnerLifecycleProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import UserLifecycleRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class DeactivateUserHandler:
    """Deactivate one user and revoke owned share artifacts first."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserLifecycleRepositoryProtocol,
        share_lifecycle: ClassroomPlannerShareOwnerLifecycleProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._share_lifecycle = share_lifecycle
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        command: DeactivateUserCommand,
    ) -> DeactivateUserResult:
        require_any_role(user=actor, roles={Role.SUPERUSER})

        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            await self._validate_superuser_floor(user)
            revoked_count = await self._share_lifecycle.revoke_for_owner_delete(
                owner_user_id=user.id,
            )

            if not user.is_active:
                return DeactivateUserResult(
                    user=user,
                    share_artifacts_revoked=revoked_count,
                )

            deactivated = await self._users.update(
                user=user.model_copy(
                    update={
                        "is_active": False,
                        "updated_at": self._clock.now(),
                    }
                )
            )

        return DeactivateUserResult(
            user=deactivated,
            share_artifacts_revoked=revoked_count,
        )

    async def _validate_superuser_floor(self, user: User) -> None:
        if user.role is not Role.SUPERUSER or not user.is_active:
            return

        active_by_role = await self._users.count_active_by_role()
        if active_by_role.get(Role.SUPERUSER, 0) <= 1:
            raise validation_error("Cannot deactivate the last active superuser.")
