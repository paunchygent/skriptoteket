from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from skriptoteket.domain.curated_apps.reagent_prep_chef.formulas import normalize_formula_key
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    ClpBand,
    ExothermicityLevel,
    HazardEntry,
)
from skriptoteket.protocols.reagent_prep_chef import ReagentPrepChefHazardStoreProtocol


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("expected string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("required text value is empty")
    return cleaned


def _clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("expected string")
    cleaned = value.strip()
    return cleaned or None


def _clean_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("expected list")
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("expected list of strings")
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
    return cleaned


class _ClpBandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_molarity: Decimal | None = None
    max_molarity: Decimal | None = None
    hazard_codes: list[str] = Field(default_factory=list)
    pictograms: list[str] = Field(default_factory=list)
    signal_word: Literal["danger", "warning"] | None = None
    notes: list[str] = Field(default_factory=list)

    _strip_hazard_codes = field_validator("hazard_codes", mode="before")(_clean_text_list)
    _strip_pictograms = field_validator("pictograms", mode="before")(_clean_text_list)
    _strip_notes = field_validator("notes", mode="before")(_clean_text_list)


class _HazardEntryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    display_name: str
    hazard_codes: list[str] = Field(default_factory=list)
    ppe: list[str] = Field(default_factory=list)
    disposal: str | None = None
    notes: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    sds_ref: str | None = None
    clp_bands: list[_ClpBandModel] = Field(default_factory=list)
    incompatibilities: list[str] = Field(default_factory=list)
    exothermicity: ExothermicityLevel | None = None
    reaction_notes: list[str] = Field(default_factory=list)

    _strip_key = field_validator("key", mode="before")(_clean_text)
    _strip_display_name = field_validator("display_name", mode="before")(_clean_text)
    _strip_hazard_codes = field_validator("hazard_codes", mode="before")(_clean_text_list)
    _strip_ppe = field_validator("ppe", mode="before")(_clean_text_list)
    _strip_notes = field_validator("notes", mode="before")(_clean_text_list)
    _strip_aliases = field_validator("aliases", mode="before")(_clean_text_list)
    _strip_incompatibilities = field_validator("incompatibilities", mode="before")(_clean_text_list)
    _strip_reaction_notes = field_validator("reaction_notes", mode="before")(_clean_text_list)
    _strip_disposal = field_validator("disposal", mode="before")(_clean_optional_text)
    _strip_sds_ref = field_validator("sds_ref", mode="before")(_clean_optional_text)


_HAZARDS_ADAPTER = TypeAdapter(list[_HazardEntryModel])


class InMemoryReagentPrepChefHazardStore(ReagentPrepChefHazardStoreProtocol):
    def __init__(self, *, hazards_path: Path) -> None:
        self._entries = _load_entries(hazards_path)
        self._lookup = _build_lookup(self._entries)

    def lookup(self, *, formula_clean: str) -> HazardEntry | None:
        return self._lookup.get(normalize_formula_key(formula_clean))

    def list_all(self) -> list[HazardEntry]:
        return list(self._entries)


def _load_entries(path: Path) -> list[HazardEntry]:
    payload = path.read_text(encoding="utf-8")
    entries = _HAZARDS_ADAPTER.validate_json(payload)
    return [_to_domain(entry) for entry in entries]


def _to_domain(entry: _HazardEntryModel) -> HazardEntry:
    clp_bands = tuple(
        ClpBand(
            min_molarity=band.min_molarity,
            max_molarity=band.max_molarity,
            hazard_codes=tuple(band.hazard_codes),
            pictograms=tuple(band.pictograms),
            signal_word=band.signal_word,
            notes=tuple(band.notes),
        )
        for band in entry.clp_bands
    )
    return HazardEntry(
        key=entry.key,
        display_name=entry.display_name,
        hazard_codes=tuple(entry.hazard_codes),
        ppe=tuple(entry.ppe),
        disposal=entry.disposal,
        notes=tuple(entry.notes),
        aliases=tuple(entry.aliases),
        sds_ref=entry.sds_ref,
        clp_bands=clp_bands,
        incompatibilities=tuple(entry.incompatibilities),
        exothermicity=entry.exothermicity,
        reaction_notes=tuple(entry.reaction_notes),
    )


def _build_lookup(entries: list[HazardEntry]) -> dict[str, HazardEntry]:
    lookup: dict[str, HazardEntry] = {}
    for entry in entries:
        lookup[normalize_formula_key(entry.key)] = entry
        for alias in entry.aliases:
            lookup[normalize_formula_key(alias)] = entry
    return lookup
