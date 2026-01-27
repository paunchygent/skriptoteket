from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.formulas import (
    normalize_formula_key,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.models import HazardEntry

_HAZARDS_PATH = Path(__file__).with_name("hazards.json")


@dataclass(frozen=True, slots=True)
class SafetyResult:
    level: Literal["curated", "unknown"]
    entry: HazardEntry | None


def lookup_safety(*, formula_clean: str) -> SafetyResult:
    entry = _load_hazards().get(normalize_formula_key(formula_clean))
    if entry is None:
        return SafetyResult(level="unknown", entry=None)
    return SafetyResult(level="curated", entry=entry)


@lru_cache(maxsize=1)
def _load_hazards() -> dict[str, HazardEntry]:
    raw = json.loads(_HAZARDS_PATH.read_text(encoding="utf-8"))
    entries = [HazardEntry.model_validate(item) for item in raw]

    lookup: dict[str, HazardEntry] = {}
    for entry in entries:
        lookup[normalize_formula_key(entry.key)] = entry
        for alias in entry.aliases:
            lookup[normalize_formula_key(alias)] = entry
    return lookup
