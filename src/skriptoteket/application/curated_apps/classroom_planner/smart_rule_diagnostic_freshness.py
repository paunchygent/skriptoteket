"""Freshness keys for Klassrumskartan solver diagnostics.

Purpose:
    Build canonical input digests for solver-owned rule diagnostics so marker
    colors can survive workspace reloads without persisting diagnostic blobs.

Relationships:
    - Consumes draft, roster, room-template, smart-rule, and assignment domain
      models from the classroom planner.
    - Used by Smart-run handlers and workspace-load rehydration before DTO
      serialization.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from hashlib import sha256

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    PlanDraft,
    RoomFixture,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    Seat,
    SeatAssignment,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_rule_diagnostics import (
    SmartRuleDiagnostic,
)

DIAGNOSTIC_FRESHNESS_SCHEMA_VERSION = "smart-rule-diagnostics:v1"


def build_diagnostic_freshness_key(
    *,
    draft: PlanDraft,
    roster: Roster,
    template: RoomTemplate,
    smart_rules: RosterSmartRules,
    seat_assignments: Iterable[SeatAssignment],
) -> str:
    """Return a canonical digest over all inputs that define diagnostics."""

    payload = {
        "schema_version": DIAGNOSTIC_FRESHNESS_SCHEMA_VERSION,
        "draft": {
            "id": str(draft.id),
            "revision": draft.revision,
        },
        "smart_rules": _smart_rules_payload(smart_rules),
        "template": _template_payload(template),
        "roster": {
            "id": str(roster.id),
            "student_ids": sorted(student.id for student in roster.students),
        },
        "seat_assignments": sorted(
            (
                {"student_id": assignment.student_id, "seat_id": assignment.seat_id}
                for assignment in seat_assignments
            ),
            key=lambda item: (item["student_id"], item["seat_id"]),
        ),
    }
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    digest = sha256(encoded.encode("utf-8")).hexdigest()
    return f"{DIAGNOSTIC_FRESHNESS_SCHEMA_VERSION}:{digest}"


def apply_diagnostic_freshness_key(
    *,
    diagnostics: tuple[SmartRuleDiagnostic, ...],
    freshness_key: str,
) -> tuple[SmartRuleDiagnostic, ...]:
    """Attach one freshness key to every diagnostic in a payload."""

    return tuple(diagnostic.with_freshness_key(freshness_key) for diagnostic in diagnostics)


def _smart_rules_payload(smart_rules: RosterSmartRules) -> dict[str, object]:
    return {
        "roster_id": str(smart_rules.roster_id),
        "revision": smart_rules.revision,
        "seating_preferences": sorted(
            (
                {
                    "student_id": preference.student_id,
                    "near_teacher": preference.near_teacher,
                }
                for preference in smart_rules.seating_preferences
            ),
            key=lambda item: str(item["student_id"]),
        ),
        "relationship_rules": sorted(
            (
                {
                    "id": rule.id,
                    "kind": rule.kind.value,
                    "student_ids": sorted(rule.student_ids),
                }
                for rule in smart_rules.relationship_rules
            ),
            key=lambda item: str(item["id"]),
        ),
        "fixed_seat_rules": sorted(
            (
                {
                    "id": rule.id,
                    "template_id": str(rule.template_id),
                    "student_id": rule.student_id,
                    "seat_id": rule.seat_id,
                }
                for rule in smart_rules.fixed_seat_rules
            ),
            key=lambda item: str(item["id"]),
        ),
    }


def _template_payload(template: RoomTemplate) -> dict[str, object]:
    return {
        "id": str(template.id),
        "grid_cols": template.grid_cols,
        "grid_rows": template.grid_rows,
        "seats": sorted(
            (_seat_payload(seat) for seat in template.seats),
            key=lambda item: str(item["id"]),
        ),
        "fixtures": sorted(
            (_fixture_payload(fixture) for fixture in template.fixtures),
            key=lambda item: str(item["id"]),
        ),
    }


def _seat_payload(seat: Seat) -> dict[str, object]:
    return {
        "id": seat.id,
        "x": seat.x,
        "y": seat.y,
        "zone": seat.zone,
    }


def _fixture_payload(fixture: RoomFixture) -> dict[str, object]:
    return {
        "id": fixture.id,
        "type": fixture.type.value,
        "x": fixture.x,
        "y": fixture.y,
        "width": fixture.width,
        "height": fixture.height,
        "label": fixture.label,
    }
