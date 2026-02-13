from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import ClpBand


class _ClpBandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_molarity: Decimal | None = None
    max_molarity: Decimal | None = None
    hazard_codes: list[str] = Field(default_factory=list)
    pictograms: list[str] = Field(default_factory=list)
    signal_word: Literal["danger", "warning"] | None = None
    notes: list[str] = Field(default_factory=list)


class _MetaEntryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    density_g_ml: Decimal | None = None
    clp_bands: list[_ClpBandModel] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class _MetaIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    as_of: str | None = None
    entries: dict[str, _MetaEntryModel] = Field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CuratedSdsMeta:
    density_g_ml: Decimal | None
    clp_bands: tuple[ClpBand, ...]
    sources: tuple[str, ...]


class CuratedSdsMetaStore:
    def __init__(self, *, path: Path) -> None:
        self._path = path
        self._index = self._load()

    def get(self, *, cid: int) -> CuratedSdsMeta | None:
        entry = self._index.entries.get(str(cid))
        if entry is None:
            return None
        return CuratedSdsMeta(
            density_g_ml=entry.density_g_ml,
            clp_bands=tuple(
                ClpBand(
                    min_molarity=band.min_molarity,
                    max_molarity=band.max_molarity,
                    hazard_codes=tuple(band.hazard_codes),
                    pictograms=tuple(band.pictograms),
                    signal_word=band.signal_word,
                    notes=tuple(band.notes),
                )
                for band in entry.clp_bands
            ),
            sources=tuple(entry.sources),
        )

    def _load(self) -> _MetaIndex:
        if not self._path.is_file():
            return _MetaIndex()
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            return _MetaIndex.model_validate(payload)
        except (OSError, ValidationError, json.JSONDecodeError):
            return _MetaIndex()
