"""Fixed-seat rule validation and seeding for Klassrumskartan smart seating.

Purpose:
    Validate hard `Fast plats` placements and convert active classroom rules
    into student-to-seat seeds for one seating run.

Relationships:
    - Consumes roster smart-rule aggregates and room templates from the
      classroom-planner domain model.
    - Raises domain validation errors before the smart-seating solver can
      persist a draft result.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    RoomTemplate,
    Roster,
    RosterSmartRules,
)
from skriptoteket.domain.errors import validation_error


def fixed_seat_rules_for_template(
    *,
    smart_rules: RosterSmartRules,
    template_id: UUID,
) -> list[FixedSeatRule]:
    """Return only fixed-seat rules scoped to the active room template."""

    return [rule for rule in smart_rules.fixed_seat_rules if rule.template_id == template_id]


def validate_fixed_seat_rules(
    *,
    roster: Roster,
    template: RoomTemplate,
    fixed_seat_rules: list[FixedSeatRule],
) -> None:
    """Validate hard fixed placements against the roster and room template."""

    valid_student_ids = {student.id for student in roster.students}
    valid_seat_ids = {seat.id for seat in template.seats}
    seen_students: set[str] = set()
    seen_seats: set[str] = set()

    for rule in fixed_seat_rules:
        if rule.template_id != template.id:
            raise validation_error("Fixed-seat rules must match the active classroom.")
        if rule.student_id not in valid_student_ids:
            raise validation_error("Fixed-seat rules must reference roster students.")
        if rule.seat_id not in valid_seat_ids:
            raise validation_error("Fixed-seat rules must reference classroom seats.")
        if rule.student_id in seen_students:
            raise validation_error("One student can have at most one fixed seat per classroom.")
        if rule.seat_id in seen_seats:
            raise validation_error("One seat can be fixed for at most one student per classroom.")
        seen_students.add(rule.student_id)
        seen_seats.add(rule.seat_id)


def build_fixed_seat_mapping(
    *,
    roster: Roster,
    template: RoomTemplate,
    smart_rules: RosterSmartRules,
) -> dict[str, str]:
    """Build the hard seeded student-to-seat mapping for one seating run."""

    fixed_rules = fixed_seat_rules_for_template(
        smart_rules=smart_rules,
        template_id=template.id,
    )
    validate_fixed_seat_rules(
        roster=roster,
        template=template,
        fixed_seat_rules=fixed_rules,
    )
    return {rule.student_id: rule.seat_id for rule in fixed_rules}
