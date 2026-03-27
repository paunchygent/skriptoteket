"""Roster-owned smart-rule handlers for the classroom planner.

This module owns the class-global smart-rule set that belongs to one roster.
It keeps smart-rule validation and persistence separate from draft-local
arrangement patches so multiple drafts for the same class reuse the same rules.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipRule,
    Roster,
    RosterSmartRules,
    StudentSeatingPreference,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _ensure_unique(values: list[str], *, label: str) -> None:
    """Raise a validation error when one request repeats stable identifiers."""

    if len(values) != len(set(values)):
        raise validation_error(f"{label} must be unique within the smart-rule set.")


def _normalize_seating_preferences(
    seating_preferences: list[StudentSeatingPreference],
) -> list[StudentSeatingPreference]:
    """Keep only active near-teacher preferences in the persisted rule set."""

    return [preference for preference in seating_preferences if preference.near_teacher]


def _validate_roster_smart_rules(
    *,
    roster: Roster,
    seating_preferences: list[StudentSeatingPreference],
    relationship_rules: list[RelationshipRule],
) -> None:
    """Validate roster-owned smart rules against the active class list."""

    valid_student_ids = {student.id for student in roster.students}
    _ensure_unique(
        [preference.student_id for preference in seating_preferences],
        label="Seating preference student IDs",
    )
    _ensure_unique([rule.id for rule in relationship_rules], label="Relationship rule IDs")

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


class GetRosterSmartRulesHandler:
    """Load roster-owned smart rules for one class."""

    def __init__(
        self,
        rosters: RosterRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> None:
        self._rosters = rosters
        self._smart_rules = smart_rules

    async def handle(self, *, roster_id: UUID, owner_user_id: UUID) -> RosterSmartRules:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))
        return await self._smart_rules.get_by_roster_id(roster_id=roster_id)


class PatchRosterSmartRulesHandler:
    """Patch roster-owned smart rules independently of draft autosave."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._smart_rules = smart_rules

    async def handle(
        self,
        *,
        roster_id: UUID,
        owner_user_id: UUID,
        expected_revision: int,
        seating_preferences: list[StudentSeatingPreference],
        relationship_rules: list[RelationshipRule],
    ) -> RosterSmartRules:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))
        seating_preferences = _normalize_seating_preferences(seating_preferences)
        if expected_revision < 0:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Roster smart-rule revision must be zero or greater.",
            )

        _validate_roster_smart_rules(
            roster=roster,
            seating_preferences=seating_preferences,
            relationship_rules=relationship_rules,
        )
        rules = RosterSmartRules(
            roster_id=roster_id,
            revision=expected_revision,
            seating_preferences=seating_preferences,
            relationship_rules=relationship_rules,
        )
        async with self._uow:
            return await self._smart_rules.save(
                rules=rules,
                expected_revision=expected_revision,
            )
