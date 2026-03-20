from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    GroupAssignment,
    PlanDraft,
    SeatAssignment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class CreateDraftHandler:
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
        template_id: UUID,
        lesson_mode_id: str,
        group_assignments: list[GroupAssignment],
        seat_assignments: list[SeatAssignment],
    ) -> PlanDraft:
        # Verify ownership of roster and template
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))

        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))

        now = self._clock.now()
        draft = PlanDraft(
            id=self._id_generator.new_uuid(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            template_id=template_id,
            lesson_mode_id=lesson_mode_id,
            revision=0,
            group_count=6,
            group_assignments=group_assignments,
            seat_assignments=seat_assignments,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            await self._drafts.save(draft=draft)
        return draft


class GetDraftHandler:
    def __init__(self, drafts: PlanDraftRepositoryProtocol) -> None:
        self._drafts = drafts

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> PlanDraft:
        draft = await self._drafts.get_by_id(draft_id=draft_id)
        if not draft or draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        return draft


class PatchDraftHandler:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._clock = clock

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        expected_revision: int | None = None,
        group_count: int | None = None,
        group_assignments: list[GroupAssignment] | None = None,
        seat_assignments: list[SeatAssignment] | None = None,
    ) -> PlanDraft:
        draft = await self._drafts.get_by_id(draft_id=draft_id)
        if not draft or draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))

        # Optimistic concurrency check
        if expected_revision is not None and draft.revision != expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    f"Draft revision mismatch. Expected {expected_revision}, got {draft.revision}."
                ),
            )

        updated = PlanDraft(
            id=draft.id,
            owner_user_id=draft.owner_user_id,
            roster_id=draft.roster_id,
            template_id=draft.template_id,
            lesson_mode_id=draft.lesson_mode_id,
            revision=draft.revision + 1,
            group_count=group_count if group_count is not None else draft.group_count,
            group_assignments=group_assignments
            if group_assignments is not None
            else draft.group_assignments,
            seat_assignments=seat_assignments
            if seat_assignments is not None
            else draft.seat_assignments,
            created_at=draft.created_at,
            updated_at=self._clock.now(),
        )

        async with self._uow:
            await self._drafts.save(draft=updated)
        return updated
