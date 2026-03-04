"""Unit tests for the hazards↔shortcards CI guard."""

from __future__ import annotations

from scripts.check_reagent_prep_chef_hazard_shortcard_alignment import evaluate_guard


def test_evaluate_guard_passes_when_all_rules_hold() -> None:
    hazards = [{"key": "NaCl", "hazard_codes": ["H319"]}]
    shortcards_payload = {
        "manual_validation": {"required": False},
        "entries": [
            {"sds_ref": "NaCl", "clp": {"h_codes": ["H319"]}},
        ],
    }

    result = evaluate_guard(hazards=hazards, shortcards_payload=shortcards_payload)

    assert result.failures == []
    assert result.backfill_candidates == []
    assert result.mismatched_non_empty == []
    assert result.missing_shortcards == []


def test_evaluate_guard_fails_when_shortcards_require_manual_validation() -> None:
    hazards = [{"key": "NaCl", "hazard_codes": ["H319"]}]
    shortcards_payload = {
        "manual_validation": {"required": True},
        "entries": [
            {"sds_ref": "NaCl", "clp": {"h_codes": ["H319"]}},
        ],
    }

    result = evaluate_guard(hazards=hazards, shortcards_payload=shortcards_payload)

    assert result.manual_validation_required is True
    assert any("manual validation is required" in item for item in result.failures)


def test_evaluate_guard_fails_on_backfill_candidate() -> None:
    hazards = [{"key": "NaCl", "hazard_codes": []}]
    shortcards_payload = {
        "manual_validation": {"required": False},
        "entries": [
            {"sds_ref": "NaCl", "clp": {"h_codes": ["H319"]}},
        ],
    }

    result = evaluate_guard(hazards=hazards, shortcards_payload=shortcards_payload)

    assert result.backfill_candidates == ["NaCl"]
    assert any("backfill candidates" in item for item in result.failures)


def test_evaluate_guard_fails_on_non_empty_mismatch_and_missing_shortcard() -> None:
    hazards = [
        {"key": "NaOH", "hazard_codes": ["H314"]},
        {"key": "KOH", "hazard_codes": ["H314"]},
    ]
    shortcards_payload = {
        "manual_validation": {"required": False},
        "entries": [
            {"sds_ref": "NaOH", "clp": {"h_codes": ["H290", "H314"]}},
        ],
    }

    result = evaluate_guard(hazards=hazards, shortcards_payload=shortcards_payload)

    assert result.mismatched_non_empty == ["NaOH"]
    assert result.missing_shortcards == ["KOH"]
    assert any("mismatches" in item for item in result.failures)
    assert any("missing corresponding shortcards" in item for item in result.failures)
