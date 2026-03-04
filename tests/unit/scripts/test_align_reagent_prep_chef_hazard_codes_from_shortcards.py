"""Unit tests for hazard-code alignment against SDS shortcards."""

from __future__ import annotations

from scripts.align_reagent_prep_chef_hazard_codes_from_shortcards import (
    apply_backfill,
    collect_alignment,
)


def test_collect_alignment_backfills_only_empty_hazard_codes() -> None:
    hazards = [
        {"key": "NaCl", "hazard_codes": []},
        {"key": "H2SO4", "hazard_codes": ["H314"]},
    ]
    shortcards_payload = {
        "manual_validation": {"required": False},
        "entries": [
            {"sds_ref": "NaCl", "clp": {"h_codes": ["H319", "H319"]}},
            {"sds_ref": "H2SO4", "clp": {"h_codes": ["H314"]}},
        ],
    }

    result = collect_alignment(hazards=hazards, shortcards_payload=shortcards_payload)

    assert result.backfill_by_key == {"NaCl": ["H319"]}
    assert result.mismatched_non_empty == []
    assert result.missing_shortcards == []


def test_collect_alignment_tracks_non_empty_mismatches_and_missing_shortcards() -> None:
    hazards = [
        {"key": "NaOH", "hazard_codes": ["H314"]},
        {"key": "KOH", "hazard_codes": ["H314"]},
    ]
    shortcards_payload = {
        "entries": [
            {"sds_ref": "NaOH", "clp": {"h_codes": ["H290", "H314"]}},
        ]
    }

    result = collect_alignment(hazards=hazards, shortcards_payload=shortcards_payload)

    assert result.backfill_by_key == {}
    assert result.mismatched_non_empty == ["NaOH"]
    assert result.missing_shortcards == ["KOH"]


def test_apply_backfill_updates_selected_keys_only() -> None:
    hazards = [
        {"key": "NaCl", "hazard_codes": []},
        {"key": "H2SO4", "hazard_codes": ["H314"]},
    ]

    updated = apply_backfill(
        hazards=hazards,
        backfill_by_key={"NaCl": ["H319"]},
    )

    assert updated[0]["hazard_codes"] == ["H319"]
    assert updated[1]["hazard_codes"] == ["H314"]
