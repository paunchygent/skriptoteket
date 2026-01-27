from __future__ import annotations

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.safety import lookup_safety


def test_lookup_safety_matches_known_formula_keys() -> None:
    assert lookup_safety(formula_clean="NaCl").level == "curated"
    assert lookup_safety(formula_clean="CuSO4·5H2O").level == "curated"


def test_lookup_safety_returns_unknown_for_missing_entries() -> None:
    assert lookup_safety(formula_clean="H2O").level == "unknown"
