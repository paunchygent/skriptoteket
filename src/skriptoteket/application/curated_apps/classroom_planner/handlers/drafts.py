"""Draft and workspace handlers for the classroom planner.

This module owns mutable planner workspace flows: creating a new draft,
hydrating the full workspace for the SPA, and patching draft-scoped planning
state with optimistic concurrency and structural validation.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PairConstraint,
    PlanDraft,
    PlanningProfile,
    RoomTemplate,
    Roster,
    SeatAssignment,
    StudentPlanningMeta,
    default_planning_profile,
    is_valid_lesson_mode_id,
)
from skriptoteket.domain.curated_apps.classroom_planner.validation import validate_workspace
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_STRUCTURAL_FINDING_CODES = {
    "invalid_lesson_mode",
    "duplicate_roster_student",
    "duplicate_template_seat",
    "duplicate_group_id",
    "duplicate_group_sort_order",
    "unknown_group_assignment_student",
    "unknown_group_assignment_group",
    "duplicate_group_assignment_student",
    "unknown_seat_assignment_student",
    "unknown_seat_assignment_seat",
    "duplicate_seat_assignment_student",
    "duplicate_seat_assignment_seat",
    "unknown_student_meta_student",
    "unknown_pair_constraint_student",
    "invalid_pair_constraint_self",
}


def _build_default_groups(
    *,
    id_generator: IdGeneratorProtocol,
    count: int = 6,
) -> list[DraftGroup]:
    return [
        DraftGroup(
            id=f"group-{index}-{id_generator.new_uuid().hex[:8]}",
            name=f"Grupp {index}",
            sort_order=index - 1,
        )
        for index in range(1, count + 1)
    ]


class CreateDraftHandler:
    """Create a new mutable planner draft and initialize its workspace."""

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
    ) -> PlanDraft:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))

        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))

        if not is_valid_lesson_mode_id(lesson_mode_id=lesson_mode_id):
            raise validation_error("Lesson mode must exist in bootstrap presets.")

        now = self._clock.now()
        draft = PlanDraft(
            id=self._id_generator.new_uuid(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            template_id=template_id,
            lesson_mode_id=lesson_mode_id,
            revision=0,
            created_at=now,
            updated_at=now,
        )
        workspace = DraftWorkspace(
            draft=draft,
            groups=_build_default_groups(id_generator=self._id_generator),
            group_assignments=[],
            seat_assignments=[],
            student_planning_meta=[],
            pair_constraints=[],
            planning_profile=default_planning_profile(),
        )
        async with self._uow:
            await self._drafts.save_workspace(workspace=workspace)
        return draft


class GetDraftHandler:
    """Load a root draft record for owner-scoped access checks."""

    def __init__(self, drafts: PlanDraftRepositoryProtocol) -> None:
        self._drafts = drafts

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> PlanDraft:
        draft = await self._drafts.get_by_id(draft_id=draft_id)
        if not draft or draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        return draft


class GetDraftWorkspaceHandler:
    """Hydrate the full planner workspace for the SPA."""

    def __init__(
        self,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
    ) -> None:
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
    ) -> ClassroomPlannerWorkspace:
        workspace, roster, template = await self._load_workspace_context(
            draft_id=draft_id,
            owner_user_id=owner_user_id,
        )
        return ClassroomPlannerWorkspace(
            draft=workspace.draft,
            roster=roster,
            template=template,
            groups=workspace.groups,
            group_assignments=workspace.group_assignments,
            seat_assignments=workspace.seat_assignments,
            student_planning_meta=workspace.student_planning_meta,
            pair_constraints=workspace.pair_constraints,
            planning_profile=workspace.planning_profile,
        )

    async def _load_workspace_context(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
    ) -> tuple[DraftWorkspace, Roster, RoomTemplate]:
        workspace = await self._drafts.get_workspace(draft_id=draft_id)
        if not workspace or workspace.draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        roster = await self._rosters.get_by_id(roster_id=workspace.draft.roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(workspace.draft.roster_id))
        template = await self._templates.get_by_id(template_id=workspace.draft.template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(workspace.draft.template_id))
        return workspace, roster, template


class PatchDraftHandler:
    """Patch mutable planner draft state with optimistic concurrency."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._rosters = rosters
        self._templates = templates
        self._clock = clock

    async def handle(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
        expected_revision: int | None = None,
        lesson_mode_id: str | None = None,
        groups: list[DraftGroup] | None = None,
        group_assignments: list[GroupAssignment] | None = None,
        seat_assignments: list[SeatAssignment] | None = None,
        student_planning_meta: list[StudentPlanningMeta] | None = None,
        pair_constraints: list[PairConstraint] | None = None,
        planning_profile: PlanningProfile | None = None,
    ) -> PlanDraft:
        workspace = await self._drafts.get_workspace(draft_id=draft_id)
        if not workspace or workspace.draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        if expected_revision is not None and workspace.draft.revision != expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Draft revision mismatch. "
                    f"Expected {expected_revision}, got {workspace.draft.revision}."
                ),
            )

        next_lesson_mode_id = lesson_mode_id or workspace.draft.lesson_mode_id
        if not is_valid_lesson_mode_id(lesson_mode_id=next_lesson_mode_id):
            raise validation_error("Lesson mode must exist in bootstrap presets.")

        updated_draft = workspace.draft.model_copy(
            update={
                "lesson_mode_id": next_lesson_mode_id,
                "revision": workspace.draft.revision + 1,
                "updated_at": self._clock.now(),
            }
        )
        updated_workspace = DraftWorkspace(
            draft=updated_draft,
            groups=groups if groups is not None else workspace.groups,
            group_assignments=(
                group_assignments if group_assignments is not None else workspace.group_assignments
            ),
            seat_assignments=(
                seat_assignments if seat_assignments is not None else workspace.seat_assignments
            ),
            student_planning_meta=(
                student_planning_meta
                if student_planning_meta is not None
                else workspace.student_planning_meta
            ),
            pair_constraints=(
                pair_constraints if pair_constraints is not None else workspace.pair_constraints
            ),
            planning_profile=planning_profile or workspace.planning_profile,
        )
        roster = await self._rosters.get_by_id(roster_id=updated_workspace.draft.roster_id)
        template = await self._templates.get_by_id(template_id=updated_workspace.draft.template_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(updated_workspace.draft.roster_id))
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(updated_workspace.draft.template_id))

        validation_result = validate_workspace(
            workspace=ClassroomPlannerWorkspace(
                draft=updated_workspace.draft,
                roster=roster,
                template=template,
                groups=updated_workspace.groups,
                group_assignments=updated_workspace.group_assignments,
                seat_assignments=updated_workspace.seat_assignments,
                student_planning_meta=updated_workspace.student_planning_meta,
                pair_constraints=updated_workspace.pair_constraints,
                planning_profile=updated_workspace.planning_profile,
            )
        )
        structural_findings = [
            finding.model_dump(mode="json")
            for finding in validation_result.findings
            if finding.code in _STRUCTURAL_FINDING_CODES
        ]
        if structural_findings:
            raise validation_error(
                "Draft workspace contains invalid references or duplicate assignments.",
                details={"findings": structural_findings},
            )

        async with self._uow:
            await self._drafts.save_workspace(workspace=updated_workspace)
        return updated_workspace.draft
