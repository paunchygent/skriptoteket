"""Shared workspace validation for classroom planner handlers.

This module centralizes the structural workspace invariants used by both the
live draft handlers and guest-upgrade import flows so every persisted planner
workspace obeys the same class, group, and seat reference rules.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftWorkspace,
    RoomTemplate,
    Roster,
)
from skriptoteket.domain.errors import validation_error


def ensure_unique(values: list[str], *, label: str) -> None:
    """Raise a validation error when a collection repeats stable identifiers."""

    if len(values) == len(set(values)):
        return
    raise validation_error(f"{label} must be unique within the planner workspace.")


def ensure_valid_workspace_structure(
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
    group_assignment_student_ids = [
        assignment.student_id for assignment in workspace.group_assignments
    ]
    seat_assignment_student_ids = [
        assignment.student_id for assignment in workspace.seat_assignments
    ]
    seat_assignment_seat_ids = [assignment.seat_id for assignment in workspace.seat_assignments]

    ensure_unique(student_ids, label="Roster student IDs")
    ensure_unique(seat_ids, label="Room seat IDs")
    ensure_unique(group_ids, label="Group IDs")
    ensure_unique(group_sort_orders, label="Group sort orders")
    ensure_unique(group_assignment_student_ids, label="Group assignment students")
    ensure_unique(seat_assignment_student_ids, label="Seat assignment students")
    ensure_unique(seat_assignment_seat_ids, label="Seat assignment seats")

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
