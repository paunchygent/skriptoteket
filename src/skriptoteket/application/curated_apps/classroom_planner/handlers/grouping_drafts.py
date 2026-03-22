"""Grouping-specific draft lifecycle handlers for the classroom planner.

This module owns grouping-only lifecycle transitions that should not be folded
into the generic resolve flow. It keeps explicit "new grouping draft" behavior
separate from ordinary draft resolution so the frontend can request a blank
grouping workspace without smuggling lifecycle semantics through the UI.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
)
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .planner_context import load_roster_and_template_for_owner
from .workspace_builders import build_initial_workspace


class CreateGroupingDraftHandler:
    """Create a brand-new blank grouping draft for one class."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._templates = templates
        self._drafts = drafts
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        template_id: UUID | None = None,
    ) -> PlanDraft:
        await load_roster_and_template_for_owner(
            rosters=self._rosters,
            templates=self._templates,
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            template_id=template_id,
        )

        now = self._clock.now()
        async with self._uow:
            await self._drafts.acquire_roster_kind_lifecycle_lock(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.GROUPING,
            )
            existing = await self._drafts.get_active_by_roster_and_kind(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.GROUPING,
            )
            if existing is not None:
                superseded = existing.model_copy(
                    update={"status": PlanDraftStatus.SUPERSEDED, "updated_at": now}
                )
                await self._drafts.save(draft=superseded)

            draft = PlanDraft(
                id=self._id_generator.new_uuid(),
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=PlanDraftKind.GROUPING,
                template_id=template_id,
                status=PlanDraftStatus.ACTIVE,
                revision=0,
                last_opened_at=now,
                created_at=now,
                updated_at=now,
            )
            await self._drafts.save_workspace(
                workspace=build_initial_workspace(draft=draft, id_generator=self._id_generator)
            )
            return draft
