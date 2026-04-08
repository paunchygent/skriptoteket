"""Authenticated guest-upgrade consumption status for Klassrumskartan.

This handler exposes the narrow authenticated read seam for the one-time
guest-upgrade ledger. It keeps the public host cookie-agnostic while giving
the authenticated host a durable answer to whether the import bridge was
meaningfully consumed.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.protocols.classroom_planner_guest_upgrade import (
    ClassroomPlannerGuestUpgradeRepositoryProtocol,
)

APP_ID = "classroom.group-seating-studio"


class GetClassroomPlannerGuestUpgradeConsumptionHandler:
    """Read the one-time guest-upgrade consumption state for one user/app."""

    def __init__(
        self,
        *,
        guest_upgrade_repository: ClassroomPlannerGuestUpgradeRepositoryProtocol,
    ) -> None:
        self._guest_upgrade_repository = guest_upgrade_repository

    async def handle(self, *, owner_user_id: UUID) -> bool:
        """Return whether the authenticated guest-upgrade bridge was consumed."""

        return await self._guest_upgrade_repository.has_consumed_upgrade(
            owner_user_id=owner_user_id,
            app_id=APP_ID,
        )
