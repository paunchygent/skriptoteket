"""Prune deleted class-list students from planner references.

Class-list saves may remove students that active grouping or seating drafts
already reference. The cleanup service removes those student ids from draft
state and roster smart rules inside the same roster update transaction.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipRule,
    RosterSmartRules,
    Student,
)
from skriptoteket.protocols.classroom_planner import (
    RosterSmartRuleRepositoryProtocol,
    RosterStudentReferenceRepositoryProtocol,
)


def removed_student_ids(*, current: list[Student], updated: list[Student]) -> set[str]:
    """Return student ids that are present in the old roster but not the new one."""
    updated_ids = {student.id for student in updated}
    return {student.id for student in current if student.id not in updated_ids}


def _prune_relationship_rule(
    *,
    rule: RelationshipRule,
    removed_student_ids: set[str],
) -> RelationshipRule | None:
    student_ids = [
        student_id for student_id in rule.student_ids if student_id not in removed_student_ids
    ]
    if len(student_ids) < 2:
        return None
    return rule.model_copy(update={"student_ids": student_ids})


def prune_smart_rules_for_removed_students(
    *,
    rules: RosterSmartRules,
    removed_student_ids: set[str],
) -> RosterSmartRules:
    """Remove deleted students from roster smart rules.

    Relationship rules with fewer than two remaining students are removed
    because keep-near and keep-apart rules cannot operate on a single student.
    """
    relationship_rules = [
        pruned_rule
        for rule in rules.relationship_rules
        if (
            pruned_rule := _prune_relationship_rule(
                rule=rule,
                removed_student_ids=removed_student_ids,
            )
        )
        is not None
    ]
    return rules.model_copy(
        update={
            "seating_preferences": [
                preference
                for preference in rules.seating_preferences
                if preference.student_id not in removed_student_ids
            ],
            "relationship_rules": relationship_rules,
            "fixed_seat_rules": [
                rule
                for rule in rules.fixed_seat_rules
                if rule.student_id not in removed_student_ids
            ],
        }
    )


class RosterStudentCleanupService:
    """Remove deleted roster students from draft and smart-rule references."""

    def __init__(
        self,
        *,
        student_references: RosterStudentReferenceRepositoryProtocol,
        smart_rules: RosterSmartRuleRepositoryProtocol,
    ) -> None:
        self._student_references = student_references
        self._smart_rules = smart_rules

    async def remove_for_roster(
        self,
        *,
        owner_user_id: UUID,
        roster_id: UUID,
        student_ids: set[str],
        updated_at: datetime,
    ) -> None:
        """Remove student ids from every roster-owned planner reference."""
        if not student_ids:
            return

        await self._student_references.remove_for_roster(
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            student_ids=student_ids,
            updated_at=updated_at,
        )
        rules = await self._smart_rules.get_by_roster_id(roster_id=roster_id)
        pruned_rules = prune_smart_rules_for_removed_students(
            rules=rules,
            removed_student_ids=student_ids,
        )
        if pruned_rules != rules:
            await self._smart_rules.save(
                rules=pruned_rules,
                expected_revision=rules.revision,
            )
