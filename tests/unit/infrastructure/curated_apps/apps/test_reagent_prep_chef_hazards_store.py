from __future__ import annotations

import json
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


def test_hazard_codes_are_backfilled_when_shortcards_have_h_codes() -> None:
    hazards_path = Path(hazards_store_module.__file__).with_name("hazards.json")
    shortcards_path = Path("data/reagent_prep_chef/sds/shortcards.json")

    hazards_payload = json.loads(hazards_path.read_text(encoding="utf-8"))
    shortcards_payload = json.loads(shortcards_path.read_text(encoding="utf-8"))

    assert isinstance(hazards_payload, list)
    assert isinstance(shortcards_payload, dict)

    shortcards_entries = shortcards_payload.get("entries")
    assert isinstance(shortcards_entries, list)
    shortcards_by_ref = {
        item.get("sds_ref"): item for item in shortcards_entries if isinstance(item, dict)
    }

    missing_hazard_codes: list[str] = []
    for hazard in hazards_payload:
        if not isinstance(hazard, dict):
            continue
        key = hazard.get("key")
        if not isinstance(key, str):
            continue
        shortcard = shortcards_by_ref.get(key)
        if not isinstance(shortcard, dict):
            continue
        clp = shortcard.get("clp")
        if not isinstance(clp, dict):
            continue
        shortcard_h_codes = [code for code in clp.get("h_codes", []) if isinstance(code, str)]
        if not shortcard_h_codes:
            continue
        hazard_codes = [code for code in hazard.get("hazard_codes", []) if isinstance(code, str)]
        if not hazard_codes:
            missing_hazard_codes.append(key)

    assert missing_hazard_codes == []
