"""Fingerprint helpers for Klassrumskartan guest smart-rule imports.

Purpose:
    Build deterministic hashes for browser-owned smart rules after they have
    been mapped into authenticated roster, template, student, and seat ids.

Relationships:
    - Used by guest-upgrade contract recomputation and asset import conflict
      checks.
    - Keeps fingerprint-only structures out of the broader guest-upgrade
      request and receipt contract module.
"""

from __future__ import annotations

import hashlib
import json
from typing import TypedDict

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    RelationshipRule,
    StudentSeatingPreference,
)


class SmartRuleFingerprintSeatingPreference(TypedDict):
    """Describe the normalized smart-rule fingerprint payload for one student."""

    student_id: str
    near_teacher: bool


class SmartRuleFingerprintRelationshipRule(TypedDict):
    """Describe the normalized smart-rule fingerprint payload for one relation."""

    kind: str
    student_ids: list[str]


class SmartRuleFingerprintFixedSeatRule(TypedDict):
    """Describe the normalized smart-rule fingerprint payload for one fixed seat."""

    template_id: str
    student_id: str
    seat_id: str


def build_smart_rule_fingerprint_seating_preference(
    preference: StudentSeatingPreference,
) -> SmartRuleFingerprintSeatingPreference:
    """Return the normalized fingerprint payload for one seating preference."""

    return {
        "student_id": preference.student_id,
        "near_teacher": preference.near_teacher,
    }


def build_smart_rule_fingerprint_relationship_rule(
    rule: RelationshipRule,
) -> SmartRuleFingerprintRelationshipRule:
    """Return the normalized fingerprint payload for one relationship rule."""

    return {
        "kind": rule.kind.value,
        "student_ids": sorted(rule.student_ids),
    }


def build_smart_rule_fingerprint_fixed_seat_rule(
    rule: FixedSeatRule,
) -> SmartRuleFingerprintFixedSeatRule:
    """Return the normalized fingerprint payload for one fixed-seat rule."""

    return {
        "template_id": str(rule.template_id),
        "student_id": rule.student_id,
        "seat_id": rule.seat_id,
    }


def build_server_smart_rule_fingerprint(
    *,
    seating_preferences: list[SmartRuleFingerprintSeatingPreference],
    relationship_rules: list[SmartRuleFingerprintRelationshipRule],
    fixed_seat_rules: list[SmartRuleFingerprintFixedSeatRule] | None = None,
) -> str:
    """Hash one roster-global smart-rule set after student and room mapping."""

    return _sha256_payload(
        {
            "seating_preferences": sorted(
                seating_preferences,
                key=lambda preference: str(preference["student_id"]),
            ),
            "relationship_rules": sorted(
                relationship_rules,
                key=lambda rule: (
                    str(rule["kind"]),
                    tuple(rule["student_ids"]),
                ),
            ),
            "fixed_seat_rules": sorted(
                fixed_seat_rules or [],
                key=lambda rule: (
                    rule["template_id"],
                    rule["student_id"],
                    rule["seat_id"],
                ),
            ),
        }
    )


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha256_payload(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value).encode('utf-8')).hexdigest()}"
