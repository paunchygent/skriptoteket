"""Stateless public Smart seating handler for guest Klassrumskartan.

Purpose:
    Run the real seating solver against the browser-owned guest snapshot
    without creating owner-scoped drafts, history, or authenticated exports.

Relationships:
    - Consumed only by the public helper route under
      `/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run`.
    - Reuses the pure smart-seating domain solver and public snapshot
      materialization helpers.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)
from skriptoteket.application.curated_apps.classroom_planner.public_smart_run_contracts import (
    PublicSmartSeatingAppliedResponse,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import solve_smart_seating
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.clock import ClockProtocol

from ..smart_rule_diagnostic_contracts import serialize_smart_rule_diagnostics
from ..smart_rule_diagnostic_freshness import (
    apply_diagnostic_freshness_key,
    build_diagnostic_freshness_key,
)
from .public_smart_run_support import (
    build_public_workspace_response,
    materialize_public_smart_workspace,
)


@dataclass(frozen=True, slots=True)
class RunPublicSmartSeatingHandler:
    """Run solver-backed Smart seating on one browser-owned guest snapshot."""

    clock: ClockProtocol

    async def handle(
        self,
        *,
        snapshot: ClassroomPlannerGuestSnapshotPayload,
        expected_revision: int,
    ) -> PublicSmartSeatingAppliedResponse:
        materialized = materialize_public_smart_workspace(
            snapshot=snapshot,
            draft_kind=PlanDraftKind.SEATING,
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
            raise validation_error("Smart seating requires Smart to be enabled.")
        if materialized.template is None:
            raise validation_error("Smart seating requires a guest classroom.")
        template = materialized.template

        smart_result = solve_smart_seating(
            roster=materialized.roster,
            template=template,
            smart_rules=materialized.smart_rules,
            current_seat_assignments=materialized.workspace.seat_assignments,
            history_checkpoints=[],
        )
        next_draft = materialized.draft_payload.model_copy(
            update={"revision": materialized.draft_payload.revision + 1}
        )
        next_domain_draft = materialized.workspace.draft.model_copy(
            update={"revision": next_draft.revision}
        )
        freshness_key = build_diagnostic_freshness_key(
            draft=next_domain_draft,
            roster=materialized.roster,
            template=template,
            smart_rules=materialized.smart_rules,
            seat_assignments=smart_result.seat_assignments,
        )
        return PublicSmartSeatingAppliedResponse(
            status="applied",
            workspace=build_public_workspace_response(
                draft_payload=next_draft,
                roster_payload=materialized.roster_payload,
                template_payload=materialized.template_payload,
                groups=materialized.workspace.groups,
                group_assignments=materialized.workspace.group_assignments,
                seat_assignments=smart_result.seat_assignments,
            ),
            used_history=False,
            message=_build_run_message(
                has_tradeoffs=smart_result.has_tradeoffs,
                unplaced_student_count=len(smart_result.unplaced_student_ids),
            ),
            rule_diagnostics=serialize_smart_rule_diagnostics(
                apply_diagnostic_freshness_key(
                    diagnostics=smart_result.rule_diagnostics,
                    freshness_key=freshness_key,
                )
            ),
        )


def _build_run_message(*, has_tradeoffs: bool, unplaced_student_count: int) -> str:
    if unplaced_student_count == 1:
        return "Smart placering klar, men 1 elev fick ingen plats."
    if unplaced_student_count > 1:
        return f"Smart placering klar, men {unplaced_student_count} elever fick ingen plats."
    if has_tradeoffs:
        return "Smart placering klar, men alla regler kunde inte uppfyllas."
    return "Smart placering klar."
