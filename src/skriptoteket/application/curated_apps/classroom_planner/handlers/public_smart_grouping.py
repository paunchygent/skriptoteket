"""Stateless public Smart grouping handler for guest Klassrumskartan.

Purpose:
    Run the real grouping solver against the browser-owned guest snapshot
    without touching authenticated persistence or owner-scoped APIs.

Relationships:
    - Consumed only by the public helper route under
      `/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run`.
    - Reuses the pure smart-grouping domain solver and public snapshot
      materialization helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)
from skriptoteket.application.curated_apps.classroom_planner.public_smart_run_contracts import (
    PublicSmartGroupingAppliedResponse,
)
from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedRoomFixture,
    NormalizedRoomSeat,
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    PlanDraftKind,
    RoomTemplate,
    SeatAssignment,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping import (
    LiveSeatingContinuityInput,
    solve_smart_grouping,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.clock import ClockProtocol

from .public_smart_run_support import (
    MaterializedPublicSmartWorkspace,
    build_public_workspace_response,
    materialize_public_smart_workspace,
)

NO_CLASSROOM_SIGNAL_MESSAGE = "Inget användbart sittschema fanns för valt klassrum."


@dataclass(frozen=True, slots=True)
class RunPublicSmartGroupingHandler:
    """Run solver-backed Smart grouping on one browser-owned guest snapshot."""

    clock: ClockProtocol

    async def handle(
        self,
        *,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        expected_revision: int,
    ) -> PublicSmartGroupingAppliedResponse:
        materialized = materialize_public_smart_workspace(
            snapshot=snapshot,
            draft_kind=PlanDraftKind.GROUPING,
            now=self.clock.now(),
        )
        if materialized.draft_payload.revision != expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Draft revision mismatch. "
                    f"Expected {expected_revision}, got {materialized.draft_payload.revision}."
                ),
            )
        if not materialized.draft_payload.smart_enabled:
            raise validation_error("Smart grouping requires Smart to be enabled.")

        live_seating = self._resolve_live_seating(snapshot=snapshot, materialized=materialized)
        smart_result = solve_smart_grouping(
            roster=materialized.roster,
            groups=materialized.workspace.groups,
            smart_rules=materialized.smart_rules,
            current_group_assignments=materialized.workspace.group_assignments,
            history_checkpoints=[],
            live_seating_continuity=live_seating,
        )
        next_draft = materialized.draft_payload.model_copy(
            update={"revision": materialized.draft_payload.revision + 1}
        )
        return PublicSmartGroupingAppliedResponse(
            status="applied",
            workspace=build_public_workspace_response(
                draft_payload=next_draft,
                roster_payload=materialized.roster_payload,
                template_payload=materialized.template_payload,
                groups=materialized.workspace.groups,
                group_assignments=smart_result.group_assignments,
                seat_assignments=materialized.workspace.seat_assignments,
            ),
            used_history=False,
            used_live_seating=live_seating is not None,
            message=_build_run_message(
                requested_live_seating=materialized.draft_payload.grouping_seating_distance_enabled,
                used_live_seating=live_seating is not None,
                has_tradeoffs=smart_result.has_tradeoffs,
            ),
        )

    def _resolve_live_seating(
        self,
        *,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        materialized: MaterializedPublicSmartWorkspace,
    ) -> LiveSeatingContinuityInput | None:
        if not materialized.draft_payload.grouping_seating_distance_enabled:
            return None
        if materialized.template is None or materialized.template_payload is None:
            return None

        seating_draft = snapshot.seating_draft
        if seating_draft is None:
            return None
        if seating_draft.roster_local_id != materialized.draft_payload.roster_local_id:
            return None
        if seating_draft.template_local_id != materialized.draft_payload.template_local_id:
            return None
        if not seating_draft.seat_assignments:
            return None
        return LiveSeatingContinuityInput(
            room_context=_build_room_context_snapshot(template=materialized.template),
            seat_assignments=[
                SeatAssignment(student_id=assignment.student_id, seat_id=assignment.seat_id)
                for assignment in seating_draft.seat_assignments
            ],
        )


def _build_run_message(
    *,
    requested_live_seating: bool,
    used_live_seating: bool,
    has_tradeoffs: bool,
) -> str:
    if has_tradeoffs:
        base_message = "Smart gruppindelning klar med bästa möjliga kompromiss."
    elif used_live_seating:
        base_message = "Smart gruppindelning klar med stöd från klassens sittschema."
    else:
        base_message = "Smart gruppindelning klar."
    if requested_live_seating and not used_live_seating:
        return f"{base_message} {NO_CLASSROOM_SIGNAL_MESSAGE}"
    return base_message


def _build_room_context_snapshot(*, template: RoomTemplate) -> SeatingRoomContextSnapshot:
    """Normalize one browser-owned room template for live seating continuity."""

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
