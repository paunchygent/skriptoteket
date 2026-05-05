"""Shared smart-rule validation for classroom planner handlers.

This module keeps the roster-owned smart-rule normalization and validation
logic reusable across the authenticated smart-rule API and guest-upgrade
import flows so both paths enforce the same roster invariants.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    RelationshipRule,
    RoomTemplate,
    Roster,
    StudentSeatingPreference,
)
from skriptoteket.domain.errors import validation_error


def ensure_unique(values: list[str], *, label: str) -> None:
    """Raise a validation error when one request repeats stable identifiers."""

    if len(values) != len(set(values)):
        raise validation_error(f"{label} must be unique within the smart-rule set.")


def normalize_seating_preferences(
    seating_preferences: list[StudentSeatingPreference],
) -> list[StudentSeatingPreference]:
    """Keep only active near-teacher preferences in the persisted rule set."""

    return [preference for preference in seating_preferences if preference.near_teacher]


def validate_roster_smart_rules(
    *,
    roster: Roster,
    seating_preferences: list[StudentSeatingPreference],
    relationship_rules: list[RelationshipRule],
    fixed_seat_rules: list[FixedSeatRule],
    templates_by_id: dict[str, RoomTemplate],
) -> None:
    """Validate roster-owned smart rules against the active class list."""

    valid_student_ids = {student.id for student in roster.students}
    ensure_unique(
        [preference.student_id for preference in seating_preferences],
        label="Seating preference student IDs",
    )
    ensure_unique([rule.id for rule in relationship_rules], label="Relationship rule IDs")
    ensure_unique([rule.id for rule in fixed_seat_rules], label="Fixed-seat rule IDs")

    for preference in seating_preferences:
        if preference.student_id not in valid_student_ids:
            raise validation_error("Seating preferences must reference roster students.")

    students_in_relationship_rules: list[str] = []
    for rule in relationship_rules:
        for student_id in rule.student_ids:
            if student_id not in valid_student_ids:
                raise validation_error("Relationship rules must reference roster students.")
            students_in_relationship_rules.append(student_id)

    if len(students_in_relationship_rules) != len(set(students_in_relationship_rules)):
        raise validation_error("One student can belong to at most one relationship rule.")

    fixed_students_by_template: set[tuple[str, str]] = set()
    fixed_seats_by_template: set[tuple[str, str]] = set()
    for fixed_rule in fixed_seat_rules:
        if fixed_rule.student_id not in valid_student_ids:
            raise validation_error("Fixed-seat rules must reference roster students.")
        template = templates_by_id.get(str(fixed_rule.template_id))
        if template is None:
            raise validation_error("Fixed-seat rules must reference owned classroom templates.")
        seat_ids = {seat.id for seat in template.seats}
        if fixed_rule.seat_id not in seat_ids:
            raise validation_error("Fixed-seat rules must reference classroom seats.")

        student_key = (str(fixed_rule.template_id), fixed_rule.student_id)
        seat_key = (str(fixed_rule.template_id), fixed_rule.seat_id)
        if student_key in fixed_students_by_template:
            raise validation_error("One student can have at most one fixed seat per classroom.")
        if seat_key in fixed_seats_by_template:
            raise validation_error("One seat can be fixed for at most one student per classroom.")
        fixed_students_by_template.add(student_key)
        fixed_seats_by_template.add(seat_key)
