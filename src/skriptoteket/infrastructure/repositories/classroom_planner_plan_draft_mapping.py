"""Mapping helpers for Klassrumskartan plan drafts.

The SQLAlchemy draft rows store draft roots, child assignments, and history
snapshots. These helpers convert hydrated ORM rows and workspace aggregates to
the domain models and deterministic snapshot dictionaries used by persistence.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import NotRequired, TypedDict

from pydantic import JsonValue

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


class WorkspaceSnapshotGroup(TypedDict):
    """One serialized group entry inside a persisted workspace history snapshot."""

    id: str
    name: str
    sort_order: int
    name_is_custom: bool


class WorkspaceSnapshotGroupAssignment(TypedDict):
    """One serialized student-to-group entry inside a history snapshot."""

    student_id: str
    group_id: str


class WorkspaceSnapshotSeatAssignment(TypedDict):
    """One serialized student-to-seat entry inside a history snapshot."""

    student_id: str
    seat_id: str


class WorkspaceSnapshot(TypedDict):
    """Serialized workspace state stored in the draft history JSONB stack.

    `template_id` is written only for grouping drafts; the parser leaves it out
    when the stored snapshot has no such key.
    """

    smart_enabled: bool
    use_history: bool
    grouping_seating_distance_enabled: bool
    groups: list[WorkspaceSnapshotGroup]
    group_assignments: list[WorkspaceSnapshotGroupAssignment]
    seat_assignments: list[WorkspaceSnapshotSeatAssignment]
    template_id: NotRequired[str | None]


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


def create_workspace_snapshot(workspace: DraftWorkspace) -> WorkspaceSnapshot:
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
    snapshot: WorkspaceSnapshot = {
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


def parse_workspace_snapshot(value: JsonValue) -> WorkspaceSnapshot:
    """Narrow a JSON history-stack entry back into the workspace snapshot shape.

    Missing flags default to False and a missing seat list to empty, as the
    undo/redo path always treated them. Missing `groups`/`group_assignments`
    keys or wrong container types raise.
    """
    if not isinstance(value, dict):
        raise TypeError("workspace history snapshot must be a dict")
    snapshot: WorkspaceSnapshot = {
        "smart_enabled": bool(value.get("smart_enabled", False)),
        "use_history": bool(value.get("use_history", False)),
        "grouping_seating_distance_enabled": bool(
            value.get("grouping_seating_distance_enabled", False)
        ),
        "groups": _snapshot_groups(value["groups"]),
        "group_assignments": _snapshot_group_assignments(value["group_assignments"]),
        "seat_assignments": _snapshot_seat_assignments(value.get("seat_assignments", [])),
    }
    if "template_id" in value:
        template_id = value["template_id"]
        snapshot["template_id"] = str(template_id) if template_id else None
    return snapshot


def _snapshot_str(entry: Mapping[str, JsonValue], key: str) -> str:
    field = entry[key]
    if not isinstance(field, str):
        raise TypeError(f"workspace history snapshot {key} must be a string")
    return field


def _snapshot_int(entry: Mapping[str, JsonValue], key: str) -> int:
    field = entry[key]
    if not isinstance(field, int):
        raise TypeError(f"workspace history snapshot {key} must be an integer")
    return field


def _snapshot_bool(entry: Mapping[str, JsonValue], key: str) -> bool:
    field = entry.get(key, False)
    if not isinstance(field, bool):
        raise TypeError(f"workspace history snapshot {key} must be a boolean")
    return field


def _snapshot_groups(value: JsonValue) -> list[WorkspaceSnapshotGroup]:
    if not isinstance(value, list):
        raise TypeError("workspace history snapshot groups must be a list")
    groups: list[WorkspaceSnapshotGroup] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise TypeError("workspace history snapshot group must be a dict")
        groups.append(
            {
                "id": _snapshot_str(entry, "id"),
                "name": _snapshot_str(entry, "name"),
                "sort_order": _snapshot_int(entry, "sort_order"),
                "name_is_custom": _snapshot_bool(entry, "name_is_custom"),
            }
        )
    return groups


def _snapshot_group_assignments(value: JsonValue) -> list[WorkspaceSnapshotGroupAssignment]:
    if not isinstance(value, list):
        raise TypeError("workspace history snapshot group_assignments must be a list")
    assignments: list[WorkspaceSnapshotGroupAssignment] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise TypeError("workspace history snapshot group assignment must be a dict")
        assignments.append(
            {
                "student_id": _snapshot_str(entry, "student_id"),
                "group_id": _snapshot_str(entry, "group_id"),
            }
        )
    return assignments


def _snapshot_seat_assignments(value: JsonValue) -> list[WorkspaceSnapshotSeatAssignment]:
    if not isinstance(value, list):
        raise TypeError("workspace history snapshot seat_assignments must be a list")
    assignments: list[WorkspaceSnapshotSeatAssignment] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise TypeError("workspace history snapshot seat assignment must be a dict")
        assignments.append(
            {
                "student_id": _snapshot_str(entry, "student_id"),
                "seat_id": _snapshot_str(entry, "seat_id"),
            }
        )
    return assignments
