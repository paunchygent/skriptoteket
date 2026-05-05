"""Smart-rule materialization for public Klassrumskartan runs.

Guest Smart runs accept browser-owned rule payloads. The helpers validate the
supported public subset and return the domain rule aggregate used by the
grouping and seating solvers.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
    GuestUpgradeSmartRuleSetPayload,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    Roster,
    RosterSmartRules,
)
from skriptoteket.domain.errors import validation_error

from .smart_rule_validation import normalize_seating_preferences, validate_roster_smart_rules

PUBLIC_SMART_RUN_MAX_RELATIONSHIP_RULES = 32
PUBLIC_SMART_RUN_MAX_RELATIONSHIP_RULE_STUDENTS = 8


def resolve_public_smart_rule_set(
    *,
    snapshot: ClassroomPlannerGuestSnapshotPayload,
    roster_local_id: str,
) -> GuestUpgradeSmartRuleSetPayload | None:
    """Resolve the browser-owned Smart rule payload for one guest roster."""
    for rule_set in snapshot.smart_rule_sets:
        if rule_set.roster_local_id == roster_local_id:
            return rule_set
    return None


def build_public_smart_rules(
    *,
    roster: Roster,
    smart_rule_payload: GuestUpgradeSmartRuleSetPayload | None,
) -> RosterSmartRules:
    """Build validated roster smart rules for an anonymous Smart run."""
    if smart_rule_payload is None:
        return RosterSmartRules(
            roster_id=roster.id,
            revision=0,
            seating_preferences=[],
            relationship_rules=[],
        )

    if len(smart_rule_payload.relationship_rules) > PUBLIC_SMART_RUN_MAX_RELATIONSHIP_RULES:
        raise validation_error(
            "Public Smart payload exceeds the supported relationship-rule count."
        )
    for rule in smart_rule_payload.relationship_rules:
        if len(rule.student_ids) > PUBLIC_SMART_RUN_MAX_RELATIONSHIP_RULE_STUDENTS:
            raise validation_error("Public Smart relationship rules exceed the supported size.")

    seating_preferences = normalize_seating_preferences(
        list(smart_rule_payload.seating_preferences)
    )
    relationship_rules = list(smart_rule_payload.relationship_rules)
    validate_roster_smart_rules(
        roster=roster,
        seating_preferences=seating_preferences,
        relationship_rules=relationship_rules,
        fixed_seat_rules=[],
        templates_by_id={},
    )
    return RosterSmartRules(
        roster_id=roster.id,
        revision=smart_rule_payload.revision,
        seating_preferences=seating_preferences,
        relationship_rules=relationship_rules,
    )
