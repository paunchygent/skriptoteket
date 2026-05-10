"""Backend-owned smart-seating run handler for Klassrumskartan.

This module keeps smart seating separate from draft patching and smart-rule
authoring. It loads the persisted draft lane plus roster-global smart rules,
optionally reads the eligible checkpoint history window, runs the pure domain
solver, and saves the chosen seating result back into the active draft.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    build_room_context_hash,
    build_room_context_snapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.fixed_seating import (
    build_fixed_seat_mapping,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftWorkspace,
    PlanDraftKind,
    RoomTemplate,
    Roster,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_rule_diagnostics import (
    SmartRuleDiagnostic,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import (
    SmartSeatingResult,
    solve_smart_seating,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
    SeatingExportCheckpointRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .workspace_builders import ensure_active_draft

NO_HISTORY_BLOCK_MESSAGE = (
    "För att använda historik behöver du först exportera "
    "ett sittschema för just det här klassrummet."
)


@dataclass(frozen=True)
class SmartSeatingAppliedResult:
    """Represent one applied smart-seating run."""

    status: Literal["applied"]
    workspace: ClassroomPlannerWorkspace
    used_history: bool
    message: str | None
    rule_diagnostics: tuple[SmartRuleDiagnostic, ...]


@dataclass(frozen=True)
class SmartSeatingBlockedResult:
    """Represent one honest blocked smart-seating run."""

    status: Literal["blocked"]
    reason: Literal["no_history"]
    message: str
    used_history: bool


SmartSeatingRunResult = SmartSeatingAppliedResult | SmartSeatingBlockedResult


class RunSmartSeatingHandler:
    """Run backend-owned smart seating for one active seating draft."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
        checkpoints: SeatingExportCheckpointRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates
        self._smart_rules = smart_rules
        self._checkpoints = checkpoints
        self._clock = clock

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        expected_revision: int,
    ) -> SmartSeatingRunResult:
        workspace = await self._drafts.get_workspace(draft_id=draft_id)
        if not workspace or workspace.draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        ensure_active_draft(draft=workspace.draft)
        if workspace.draft.draft_kind is not PlanDraftKind.SEATING:
            raise validation_error("Smart seating requires a seating draft.")
        if not workspace.draft.smart_enabled:
            raise validation_error("Smart seating requires Smart to be enabled.")
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

        smart_rules = await self._smart_rules.get_by_roster_id(roster_id=workspace.draft.roster_id)
        build_fixed_seat_mapping(roster=roster, template=template, smart_rules=smart_rules)
        hydrated_workspace = self._hydrate_workspace(
            workspace=workspace,
            roster=roster,
            template=template,
        )
        room_context = build_room_context_snapshot(workspace=hydrated_workspace)
        room_context_hash = build_room_context_hash(room_context=room_context)
        history = await self._load_history_window(
            roster_id=workspace.draft.roster_id,
            room_context_hash=room_context_hash,
            use_history=workspace.draft.use_history,
        )
        if workspace.draft.use_history and not history:
            return SmartSeatingBlockedResult(
                status="blocked",
                reason="no_history",
                message=NO_HISTORY_BLOCK_MESSAGE,
                used_history=False,
            )

        smart_result = solve_smart_seating(
            roster=roster,
            template=template,
            smart_rules=smart_rules,
            current_seat_assignments=workspace.seat_assignments,
            history_checkpoints=history,
        )
        persisted_workspace = await self._persist_result(
            workspace=workspace,
            seat_assignments=smart_result,
        )
        return SmartSeatingAppliedResult(
            status="applied",
            workspace=self._hydrate_workspace(
                workspace=persisted_workspace,
                roster=roster,
                template=template,
            ),
            used_history=bool(history),
            message=_build_run_message(
                used_history=bool(history),
                has_tradeoffs=smart_result.has_tradeoffs,
                unplaced_student_count=len(smart_result.unplaced_student_ids),
            ),
            rule_diagnostics=smart_result.rule_diagnostics,
        )

    async def _load_template(
        self, *, template_id: UUID | None, owner_user_id: UUID
    ) -> RoomTemplate:
        if template_id is None:
            raise validation_error("Smart seating requires a classroom.")
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))
        return template

    async def _load_history_window(
        self,
        *,
        roster_id: UUID,
        room_context_hash: str,
        use_history: bool,
    ):
        if not use_history:
            return []
        return await self._checkpoints.list_recent_for_roster_and_room_context(
            roster_id=roster_id,
            room_context_hash=room_context_hash,
        )

    async def _persist_result(
        self,
        *,
        workspace: DraftWorkspace,
        seat_assignments: SmartSeatingResult,
    ) -> DraftWorkspace:
        updated_workspace = DraftWorkspace(
            draft=workspace.draft.model_copy(
                update={
                    "revision": workspace.draft.revision + 1,
                    "updated_at": self._clock.now(),
                }
            ),
            groups=workspace.groups,
            group_assignments=workspace.group_assignments,
            seat_assignments=seat_assignments.seat_assignments,
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
        template: RoomTemplate,
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
    *, used_history: bool, has_tradeoffs: bool, unplaced_student_count: int
) -> str:
    if unplaced_student_count == 1:
        return "Smart placering klar, men 1 elev fick ingen plats."
    if unplaced_student_count > 1:
        return f"Smart placering klar, men {unplaced_student_count} elever fick ingen plats."
    if has_tradeoffs:
        return "Smart placering klar, men alla regler kunde inte uppfyllas."
    if used_history:
        return "Smart placering klar med stöd av tidigare exporter."
    return "Smart placering klar."
