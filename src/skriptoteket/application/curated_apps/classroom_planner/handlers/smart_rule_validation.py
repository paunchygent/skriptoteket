"""Shared smart-rule validation for classroom planner handlers.

This module keeps the roster-owned smart-rule normalization and validation
logic reusable across the authenticated smart-rule API and guest-upgrade
import flows so both paths enforce the same roster invariants.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipRule,
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
) -> None:
    """Validate roster-owned smart rules against the active class list."""

    valid_student_ids = {student.id for student in roster.students}
    ensure_unique(
        [preference.student_id for preference in seating_preferences],
        label="Seating preference student IDs",
    )
    ensure_unique([rule.id for rule in relationship_rules], label="Relationship rule IDs")

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
