from __future__ import annotations

from pathlib import Path

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import (
    hazards_store as hazards_store_module,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.hazards_store import (
    InMemoryReagentPrepChefHazardStore,
)


def test_lookup_matches_known_formula_keys() -> None:
    hazards_path = Path(hazards_store_module.__file__).with_name("hazards.json")
    store = InMemoryReagentPrepChefHazardStore(hazards_path=hazards_path)

    assert store.lookup(formula_clean="NaCl") is not None
    assert store.lookup(formula_clean="CuSO4·5H2O") is not None


def test_lookup_returns_none_for_missing_entries() -> None:
    hazards_path = Path(hazards_store_module.__file__).with_name("hazards.json")
    store = InMemoryReagentPrepChefHazardStore(hazards_path=hazards_path)

    assert store.lookup(formula_clean="H2O") is None
