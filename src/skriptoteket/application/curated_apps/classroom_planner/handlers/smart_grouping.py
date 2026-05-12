"""Backend-owned smart-grouping run handler for Klassrumskartan.

Purpose:
    Keep smart grouping separate from draft patching and roster smart-rule
    authoring while introducing the new grouping-history and live
    seating-continuity seams.

Relationships:
    - consumes the pure smart-grouping domain solver
    - loads owner-scoped draft, rule, history, and live seating inputs through
      protocols
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedRoomFixture,
    NormalizedRoomSeat,
    SeatingRoomContextSnapshot,
    build_room_context_hash,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftWorkspace,
    PlanDraftKind,
    RoomTemplate,
    Roster,
    SeatAssignment,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping import (
    LiveSeatingContinuityInput,
    SmartGroupingResult,
    solve_smart_grouping,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
    SeatingExportCheckpointRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .workspace_builders import ensure_active_draft

NO_CLASSROOM_SIGNAL_MESSAGE = "Inget användbart sittschema fanns för valt klassrum."


@dataclass(frozen=True)
class SmartGroupingAppliedResult:
    """Represent one applied smart-grouping run."""

    status: Literal["applied"]
    workspace: ClassroomPlannerWorkspace
    used_history: bool
    used_live_seating: bool
    message: str | None


SmartGroupingRunResult = SmartGroupingAppliedResult


class RunSmartGroupingHandler:
    """Run backend-owned smart grouping for one active grouping draft."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
        grouping_checkpoints: GroupingExportCheckpointRepositoryProtocol,
        seating_checkpoints: SeatingExportCheckpointRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates
        self._smart_rules = smart_rules
        self._grouping_checkpoints = grouping_checkpoints
        self._seating_checkpoints = seating_checkpoints
        self._clock = clock

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        expected_revision: int,
    ) -> SmartGroupingRunResult:
        workspace = await self._drafts.get_workspace(draft_id=draft_id)
        if not workspace or workspace.draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        ensure_active_draft(draft=workspace.draft)
        if workspace.draft.draft_kind is not PlanDraftKind.GROUPING:
            raise validation_error("Smart grouping requires a grouping draft.")
        if not workspace.draft.smart_enabled:
            raise validation_error("Smart grouping requires Smart to be enabled.")
        if workspace.draft.revision != expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Draft revision mismatch. "
                    f"Expected {expected_revision}, got {workspace.draft.revision}."
                ),
            )

        roster = await self._rosters.get_by_id(roster_id=workspace.draft.roster_id)
        template = await self._load_template(
            template_id=workspace.draft.template_id,
            owner_user_id=owner_user_id,
        )
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(workspace.draft.roster_id))

        classroom_awareness_requested = (
            workspace.draft.grouping_seating_distance_enabled and template is not None
        )
        smart_rules = await self._smart_rules.get_by_roster_id(roster_id=workspace.draft.roster_id)
        history = await self._load_history_window(
            roster_id=workspace.draft.roster_id,
            use_history=workspace.draft.use_history,
        )
        live_seating = await self._load_live_seating_continuity(
            owner_user_id=owner_user_id,
            roster_id=workspace.draft.roster_id,
            template=template,
            enabled=workspace.draft.grouping_seating_distance_enabled,
        )
        smart_result = solve_smart_grouping(
            roster=roster,
            groups=workspace.groups,
            smart_rules=smart_rules,
            current_group_assignments=workspace.group_assignments,
            history_checkpoints=history,
            live_seating_continuity=live_seating,
        )
        persisted_workspace = await self._persist_result(
            workspace=workspace,
            group_assignments=smart_result,
        )
        return SmartGroupingAppliedResult(
            status="applied",
            workspace=self._hydrate_workspace(
                workspace=persisted_workspace,
                roster=roster,
                template=template,
            ),
            used_history=bool(history),
            used_live_seating=live_seating is not None,
            message=_build_run_message(
                requested_live_seating=classroom_awareness_requested,
                used_history=bool(history),
                used_live_seating=live_seating is not None,
                has_tradeoffs=smart_result.has_tradeoffs,
            ),
        )

    async def _load_template(
        self, *, template_id: UUID | None, owner_user_id: UUID
    ) -> RoomTemplate | None:
        if template_id is None:
            return None
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))
        return template

    async def _load_history_window(self, *, roster_id: UUID, use_history: bool):
        if not use_history:
            return []
        return await self._grouping_checkpoints.list_recent_for_roster(roster_id=roster_id)

    async def _load_live_seating_continuity(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        template: RoomTemplate | None,
        enabled: bool,
    ) -> LiveSeatingContinuityInput | None:
        if not enabled or template is None:
            return None
        active_seating = await self._drafts.get_active_by_roster_and_kind(
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
        )
        if active_seating is not None:
            active_workspace = await self._drafts.get_workspace(draft_id=active_seating.id)
            if (
                active_workspace is not None
                and active_workspace.draft.template_id == template.id
                and active_workspace.draft.template_id is not None
                and active_workspace.seat_assignments
            ):
                template = await self._templates.get_by_id(
                    template_id=active_workspace.draft.template_id
                )
                if template is not None and template.owner_user_id == owner_user_id:
                    return LiveSeatingContinuityInput(
                        room_context=_build_room_context_snapshot(template=template),
                        seat_assignments=list(active_workspace.seat_assignments),
                    )

        if template is None:
            return None
        room_context_hash = build_room_context_hash(
            room_context=_build_room_context_snapshot(template=template)
        )
        latest_checkpoint = await self._seating_checkpoints.get_latest_for_roster_and_room_context(
            roster_id=roster_id,
            room_context_hash=room_context_hash,
        )
        if latest_checkpoint is None:
            return None
        return LiveSeatingContinuityInput(
            room_context=latest_checkpoint.room_context,
            seat_assignments=[
                SeatAssignment(student_id=placement.student_id, seat_id=placement.seat_id)
                for placement in latest_checkpoint.seating_snapshot.placed_assignments
            ],
        )

    async def _persist_result(
        self,
        *,
        workspace: DraftWorkspace,
        group_assignments: SmartGroupingResult,
    ) -> DraftWorkspace:
        updated_workspace = DraftWorkspace(
            draft=workspace.draft.model_copy(
                update={
                    "revision": workspace.draft.revision + 1,
                    "updated_at": self._clock.now(),
                }
            ),
            groups=workspace.groups,
            group_assignments=group_assignments.group_assignments,
            seat_assignments=workspace.seat_assignments,
            history_status=workspace.history_status,
        )
        async with self._uow:
            await self._drafts.save_workspace(workspace=updated_workspace)
            persisted_workspace = await self._drafts.get_workspace(draft_id=workspace.draft.id)
        if persisted_workspace is None:
            raise not_found("PlanDraft", str(workspace.draft.id))
        return persisted_workspace

    def _hydrate_workspace(
        self,
        *,
        workspace: DraftWorkspace,
        roster: Roster,
        template: RoomTemplate | None,
    ) -> ClassroomPlannerWorkspace:
        return ClassroomPlannerWorkspace(
            draft=workspace.draft,
            roster=roster,
            template=template,
            groups=workspace.groups,
            group_assignments=workspace.group_assignments,
            seat_assignments=workspace.seat_assignments,
            history_status=workspace.history_status,
        )


def _build_run_message(
    *,
    requested_live_seating: bool,
    used_history: bool,
    used_live_seating: bool,
    has_tradeoffs: bool,
) -> str:
    if has_tradeoffs:
        base_message = "Smart gruppindelning klar, men alla regler kunde inte uppfyllas."
    elif used_history and used_live_seating:
        base_message = "Smart gruppindelning klar med historik och stöd från klassens sittschema."
    elif used_history:
        base_message = "Smart gruppindelning klar med stöd av tidigare gruppindelningar."
    elif used_live_seating:
        base_message = "Smart gruppindelning klar med stöd från klassens sittschema."
    else:
        base_message = "Smart gruppindelning klar."
    if requested_live_seating and not used_live_seating:
        return f"{base_message} {NO_CLASSROOM_SIGNAL_MESSAGE}"
    return base_message


def _build_room_context_snapshot(*, template: RoomTemplate) -> SeatingRoomContextSnapshot:
    """Normalize one room template for seating-history fallback lookup."""

    return SeatingRoomContextSnapshot(
        grid_cols=template.grid_cols,
        grid_rows=template.grid_rows,
        seats=[
            NormalizedRoomSeat(id=seat.id, x=seat.x, y=seat.y, zone=seat.zone)
            for seat in sorted(template.seats, key=lambda seat: (seat.id, seat.x, seat.y))
        ],
        fixtures=[
            NormalizedRoomFixture(
                id=fixture.id,
                type=fixture.type,
                x=fixture.x,
                y=fixture.y,
                width=fixture.width,
                height=fixture.height,
                label=fixture.label,
            )
            for fixture in sorted(
                template.fixtures,
                key=lambda fixture: (
                    fixture.id,
                    fixture.type.value,
                    fixture.x,
                    fixture.y,
                    fixture.width,
                    fixture.height,
                    fixture.label or "",
                ),
            )
        ],
    )
