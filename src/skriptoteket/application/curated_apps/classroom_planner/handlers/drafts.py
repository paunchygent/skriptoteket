"""Draft and workspace handlers for the classroom planner.

This module owns the mutable planner workspace flows that remain in the active
fundamentals contract: resolving one active draft per class and draft kind,
hydrating that workspace for the SPA, abandoning drafts, and patching
draft-scoped grouping, seating, and student-note state with optimistic
concurrency.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    ResumablePlanDraft,
    RoomTemplate,
    Roster,
    SeatAssignment,
    StudentPlanningMeta,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .planner_context import load_roster_and_template_for_owner
from .workspace_builders import (
    build_initial_workspace,
    build_recontextualized_workspace,
    ensure_active_draft,
)


def _ensure_unique(values: list[str], *, label: str) -> None:
    """Raise a validation error when a collection repeats stable identifiers."""

    if len(values) == len(set(values)):
        return
    raise validation_error(f"{label} must be unique within the planner workspace.")


def _validate_workspace_structure(
    *,
    workspace: DraftWorkspace,
    roster: Roster,
    template: RoomTemplate | None,
) -> None:
    """Validate that draft references stay inside the selected class and room."""

    student_ids = [student.id for student in roster.students]
    seat_ids = [seat.id for seat in template.seats] if template else []
    group_ids = [group.id for group in workspace.groups]
    group_sort_orders = [str(group.sort_order) for group in workspace.groups]
    meta_student_ids = [meta.student_id for meta in workspace.student_planning_meta]
    group_assignment_student_ids = [
        assignment.student_id for assignment in workspace.group_assignments
    ]
    seat_assignment_student_ids = [
        assignment.student_id for assignment in workspace.seat_assignments
    ]
    seat_assignment_seat_ids = [assignment.seat_id for assignment in workspace.seat_assignments]

    _ensure_unique(student_ids, label="Roster student IDs")
    _ensure_unique(seat_ids, label="Room seat IDs")
    _ensure_unique(group_ids, label="Group IDs")
    _ensure_unique(group_sort_orders, label="Group sort orders")
    _ensure_unique(meta_student_ids, label="Student metadata rows")
    _ensure_unique(group_assignment_student_ids, label="Group assignment students")
    _ensure_unique(seat_assignment_student_ids, label="Seat assignment students")
    _ensure_unique(seat_assignment_seat_ids, label="Seat assignment seats")

    valid_student_ids = set(student_ids)
    valid_seat_ids = set(seat_ids)
    valid_group_ids = set(group_ids)

    for group_assignment in workspace.group_assignments:
        if group_assignment.student_id not in valid_student_ids:
            raise validation_error("Group assignments must reference roster students.")
        if group_assignment.group_id not in valid_group_ids:
            raise validation_error("Group assignments must reference existing groups.")

    for seat_assignment in workspace.seat_assignments:
        if template is None:
            raise validation_error("Seat assignments require a classroom context.")
        if seat_assignment.student_id not in valid_student_ids:
            raise validation_error("Seat assignments must reference roster students.")
        if seat_assignment.seat_id not in valid_seat_ids:
            raise validation_error("Seat assignments must reference room seats.")

    for meta in workspace.student_planning_meta:
        if meta.student_id not in valid_student_ids:
            raise validation_error("Student notes must reference roster students.")


async def _get_owned_active_draft(
    *,
    drafts: PlanDraftRepositoryProtocol,
    draft_id: UUID,
    owner_user_id: UUID,
) -> PlanDraft:
    """Load the current active draft and reject foreign or inactive targets."""

    draft = await drafts.get_by_id(draft_id=draft_id)
    if not draft or draft.owner_user_id != owner_user_id:
        raise not_found("PlanDraft", str(draft_id))
    ensure_active_draft(draft=draft)
    return draft


class ResolveDraftHandler:
    """Resolve the active mutable draft for one class and draft kind."""

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
        draft_kind: PlanDraftKind,
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
                draft_kind=draft_kind,
            )
            existing = await self._drafts.get_active_by_roster_and_kind(
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=draft_kind,
            )
            if existing is not None:
                updated = existing.model_copy(
                    update={
                        "template_id": template_id,
                        "last_opened_at": now,
                        "updated_at": now,
                    }
                )
                if existing.template_id != template_id:
                    workspace = await self._drafts.get_workspace(draft_id=existing.id)
                    if workspace is None:
                        raise not_found("PlanDraft", str(existing.id))

                    if draft_kind == PlanDraftKind.SEATING:
                        updated_workspace = build_recontextualized_workspace(
                            workspace=workspace,
                            draft=updated,
                        )
                    else:
                        updated_workspace = workspace.model_copy(update={"draft": updated})

                    await self._drafts.save_workspace(workspace=updated_workspace)
                else:
                    await self._drafts.save(draft=updated)
                return updated

            draft = PlanDraft(
                id=self._id_generator.new_uuid(),
                owner_user_id=owner_user_id,
                roster_id=roster_id,
                draft_kind=draft_kind,
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


class GetResumableDraftHandler:
    """Return the latest resumable draft for the landing page."""

    def __init__(self, drafts: PlanDraftRepositoryProtocol) -> None:
        self._drafts = drafts

    async def handle(self, *, owner_user_id: UUID) -> ResumablePlanDraft | None:
        return await self._drafts.get_latest_resumable(owner_user_id=owner_user_id)


class UndoDraftHandler:
    """Step backward in the active draft history stack."""

    def __init__(self, uow: UnitOfWorkProtocol, drafts: PlanDraftRepositoryProtocol) -> None:
        self._uow = uow
        self._drafts = drafts

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> DraftWorkspace:
        async with self._uow:
            await _get_owned_active_draft(
                drafts=self._drafts,
                draft_id=draft_id,
                owner_user_id=owner_user_id,
            )
            workspace = await self._drafts.undo(draft_id=draft_id)
            if workspace is None:
                # If we can't undo (no history or at start), just return current
                workspace = await self._drafts.get_workspace(draft_id=draft_id)
                if not workspace:
                    raise not_found("PlanDraft", str(draft_id))
            return workspace


class RedoDraftHandler:
    """Step forward in the active draft history stack."""

    def __init__(self, uow: UnitOfWorkProtocol, drafts: PlanDraftRepositoryProtocol) -> None:
        self._uow = uow
        self._drafts = drafts

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> DraftWorkspace:
        async with self._uow:
            await _get_owned_active_draft(
                drafts=self._drafts,
                draft_id=draft_id,
                owner_user_id=owner_user_id,
            )
            workspace = await self._drafts.redo(draft_id=draft_id)
            if workspace is None:
                # If we can't redo (at tip), just return current
                workspace = await self._drafts.get_workspace(draft_id=draft_id)
                if not workspace:
                    raise not_found("PlanDraft", str(draft_id))
            return workspace


class AbandonDraftHandler:
    """Mark the current teacher draft as intentionally abandoned."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        drafts: PlanDraftRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._drafts = drafts
        self._clock = clock

    async def handle(self, *, draft_id: UUID, owner_user_id: UUID) -> PlanDraft:
        draft = await self._drafts.get_by_id(draft_id=draft_id)
        if not draft or draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        if draft.status != PlanDraftStatus.ACTIVE:
            return draft

        now = self._clock.now()
        async with self._uow:
            await self._drafts.acquire_roster_kind_lifecycle_lock(
                owner_user_id=owner_user_id,
                roster_id=draft.roster_id,
                draft_kind=draft.draft_kind,
            )
            current = await self._drafts.get_by_id(draft_id=draft_id)
            if current is None or current.owner_user_id != owner_user_id:
                raise not_found("PlanDraft", str(draft_id))
            if current.status != PlanDraftStatus.ACTIVE:
                return current
            abandoned = current.model_copy(
                update={"status": PlanDraftStatus.ABANDONED, "updated_at": now}
            )
            await self._drafts.save(draft=abandoned)
            return abandoned


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
        )

    async def _load_workspace_context(
        self,
        *,
        draft_id: UUID,
        owner_user_id: UUID,
    ) -> tuple[DraftWorkspace, Roster, RoomTemplate | None]:
        workspace = await self._drafts.get_workspace(draft_id=draft_id)
        if not workspace or workspace.draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        roster = await self._rosters.get_by_id(roster_id=workspace.draft.roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(workspace.draft.roster_id))
        template = None
        if workspace.draft.template_id is not None:
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
        groups: list[DraftGroup] | None = None,
        group_assignments: list[GroupAssignment] | None = None,
        seat_assignments: list[SeatAssignment] | None = None,
        student_planning_meta: list[StudentPlanningMeta] | None = None,
    ) -> ClassroomPlannerWorkspace:
        workspace = await self._drafts.get_workspace(draft_id=draft_id)
        if not workspace or workspace.draft.owner_user_id != owner_user_id:
            raise not_found("PlanDraft", str(draft_id))
        ensure_active_draft(draft=workspace.draft)
        if expected_revision is not None and workspace.draft.revision != expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=(
                    "Draft revision mismatch. "
                    f"Expected {expected_revision}, got {workspace.draft.revision}."
                ),
            )

        updated_workspace = DraftWorkspace(
            draft=workspace.draft.model_copy(
                update={
                    "revision": workspace.draft.revision + 1,
                    "updated_at": self._clock.now(),
                }
            ),
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
        )
        roster = await self._rosters.get_by_id(roster_id=updated_workspace.draft.roster_id)
        template = None
        if updated_workspace.draft.template_id is not None:
            template = await self._templates.get_by_id(
                template_id=updated_workspace.draft.template_id
            )
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(updated_workspace.draft.roster_id))
        if updated_workspace.draft.template_id is not None and (
            not template or template.owner_user_id != owner_user_id
        ):
            raise not_found("RoomTemplate", str(updated_workspace.draft.template_id))

        _validate_workspace_structure(
            workspace=updated_workspace,
            roster=roster,
            template=template,
        )

        async with self._uow:
            await self._drafts.save_workspace(workspace=updated_workspace)
            persisted_workspace = await self._drafts.get_workspace(draft_id=draft_id)

        if persisted_workspace is None:
            raise not_found("PlanDraft", str(draft_id))

        return ClassroomPlannerWorkspace(
            draft=persisted_workspace.draft,
            roster=roster,
            template=template,
            groups=persisted_workspace.groups,
            group_assignments=persisted_workspace.group_assignments,
            seat_assignments=persisted_workspace.seat_assignments,
            student_planning_meta=persisted_workspace.student_planning_meta,
            history_status=persisted_workspace.history_status,
        )
