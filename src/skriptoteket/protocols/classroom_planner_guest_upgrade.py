"""Protocols for Klassrumskartan authenticated guest-upgrade persistence seams.

Purpose:
    Define the narrow lookup seam needed by the authenticated guest-upgrade
    flow without spreading import-specific concerns across the existing planner
    repositories.

Relationships:
    - Consumed by `application.curated_apps.classroom_planner.handlers.guest_upgrade`.
    - Implemented by a small SQLAlchemy-backed repository under
      `infrastructure.repositories`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraft


class ClassroomPlannerGuestUpgradeRepositoryProtocol(Protocol):
    """Lookup import-specific planner artifacts for idempotent guest upgrades."""

    async def has_consumed_upgrade(
        self,
        *,
        owner_user_id: UUID,
        app_id: str,
    ) -> bool:
        """Return whether the one-time guest-upgrade bridge was already consumed."""

    async def record_upgrade_consumption(
        self,
        *,
        owner_user_id: UUID,
        app_id: str,
        snapshot_id: str,
        consumed_at: datetime,
    ) -> None:
        """Persist the first meaningful guest-upgrade consumption fact."""

    async def get_imported_draft_by_identity(
        self,
        *,
        owner_user_id: UUID,
        guest_import_identity: str,
    ) -> PlanDraft | None:
        """Return an imported historical draft when the same import already exists."""

    async def grouping_checkpoint_exists(
        self,
        *,
        roster_id: UUID,
        assignment_hash: str,
    ) -> bool:
        """Return whether a grouping checkpoint with the same identity already exists."""

    async def seating_checkpoint_exists(
        self,
        *,
        roster_id: UUID,
        room_context_hash: str,
        assignment_hash: str,
    ) -> bool:
        """Return whether a seating checkpoint with the same identity already exists."""
