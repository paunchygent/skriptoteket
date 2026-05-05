"""Mapping helpers for Klassrumskartan plan drafts.

The SQLAlchemy draft rows store draft roots, child assignments, and history
snapshots. These helpers convert hydrated ORM rows and workspace aggregates to
the domain models and deterministic snapshot dictionaries used by persistence.
"""

from __future__ import annotations

from typing import Any

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    DraftGroup,
    DraftHistoryStatus,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    PlanDraftSummary,
    SeatAssignment,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    PlanDraftModel,
)


def to_draft(model: PlanDraftModel) -> PlanDraft:
    """Map one draft ORM row to the active domain aggregate."""
    task_entry_classroom_selection_mode = (
        ClassroomSelectionMode.OPTIONAL
        if model.task_entry_classroom_selection_mode is None
        else ClassroomSelectionMode(model.task_entry_classroom_selection_mode)
    )

    return PlanDraft(
        id=model.id,
        owner_user_id=model.owner_user_id,
        roster_id=model.roster_id,
        draft_kind=PlanDraftKind(model.draft_kind),
        template_id=model.template_id,
        task_entry_classroom_selection_mode=task_entry_classroom_selection_mode,
        smart_enabled=model.smart_enabled,
        use_history=model.use_history,
        grouping_seating_distance_enabled=model.grouping_seating_distance_enabled,
        status=PlanDraftStatus(model.status),
        guest_import_identity=model.guest_import_identity,
        revision=model.revision,
        last_opened_at=model.last_opened_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_workspace(model: PlanDraftModel) -> DraftWorkspace:
    """Map one hydrated draft ORM row to the active workspace aggregate."""
    history_stack = model.history_stack or []
    undo_index = model.undo_index if model.undo_index is not None else 0
    history_status = DraftHistoryStatus(
        can_undo=undo_index > 0,
        can_redo=undo_index < len(history_stack) - 1,
    )

    return DraftWorkspace(
        draft=to_draft(model),
        groups=[
            DraftGroup(
                id=group.group_id,
                name=group.name,
                sort_order=group.sort_order,
                name_is_custom=group.name_is_custom,
            )
            for group in model.groups
        ],
        group_assignments=[
            GroupAssignment(student_id=assignment.student_id, group_id=assignment.group_id)
            for assignment in model.group_assignments
        ],
        seat_assignments=[
            SeatAssignment(student_id=assignment.student_id, seat_id=assignment.seat_id)
            for assignment in model.seat_assignments
        ],
        history_status=history_status,
    )


def to_draft_summary(
    model: PlanDraftModel,
    *,
    template_name: str | None,
) -> PlanDraftSummary:
    """Map one draft row plus template label to the compact summary model."""
    return PlanDraftSummary(
        id=model.id,
        draft_kind=PlanDraftKind(model.draft_kind),
        template_id=model.template_id,
        template_name=template_name,
        status=PlanDraftStatus(model.status),
        revision=model.revision,
        last_opened_at=model.last_opened_at,
        updated_at=model.updated_at,
    )


def create_workspace_snapshot(workspace: DraftWorkspace) -> dict[str, Any]:
    """Create a deterministic history snapshot for one workspace aggregate."""
    ordered_groups = sorted(workspace.groups, key=lambda group: (group.sort_order, group.id))
    ordered_group_assignments = sorted(
        workspace.group_assignments,
        key=lambda assignment: (assignment.student_id, assignment.group_id),
    )
    ordered_seat_assignments = sorted(
        workspace.seat_assignments,
        key=lambda assignment: (assignment.student_id, assignment.seat_id),
    )
    snapshot: dict[str, Any] = {
        "smart_enabled": workspace.draft.smart_enabled,
        "use_history": workspace.draft.use_history,
        "grouping_seating_distance_enabled": workspace.draft.grouping_seating_distance_enabled,
        "groups": [
            {
                "id": group.id,
                "name": group.name,
                "sort_order": group.sort_order,
                "name_is_custom": group.name_is_custom,
            }
            for group in ordered_groups
        ],
        "group_assignments": [
            {"student_id": assignment.student_id, "group_id": assignment.group_id}
            for assignment in ordered_group_assignments
        ],
        "seat_assignments": [
            {"student_id": assignment.student_id, "seat_id": assignment.seat_id}
            for assignment in ordered_seat_assignments
        ],
    }
    if workspace.draft.draft_kind == PlanDraftKind.GROUPING:
        snapshot["template_id"] = (
            str(workspace.draft.template_id) if workspace.draft.template_id else None
        )
    return snapshot
