from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    ClpBand,
    ExothermicityLevel,
    HazardEntry,
    HazardSdsData,
    SdsFetchResult,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.reagent_prep_chef import (
    ReagentPrepChefSdsFetcherProtocol,
    ReagentPrepChefSdsIndexStoreProtocol,
)


class _ClpBandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_molarity: float | None = None
    max_molarity: float | None = None
    hazard_codes: list[str] = Field(default_factory=list)
    pictograms: list[str] = Field(default_factory=list)
    signal_word: str | None = None
    notes: list[str] = Field(default_factory=list)


class _SdsIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    display_name: str
    sds_ref: str
    file_name: str
    media_type: str
    sha256: str
    source_url: str
    retrieved_at: str
    hazard_codes: list[str] = Field(default_factory=list)
    pictograms: list[str] = Field(default_factory=list)
    signal_word: str | None = None
    clp_bands: list[_ClpBandModel] = Field(default_factory=list)
    incompatibilities: list[str] = Field(default_factory=list)
    exothermicity: ExothermicityLevel | None = None
    reaction_notes: list[str] = Field(default_factory=list)
    density_g_ml: float | None = None
    sources: list[str] = Field(default_factory=list)


class _SdsIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    entries: dict[str, _SdsIndexEntry] = Field(default_factory=dict)


class FileSystemReagentPrepChefSdsIndexStore(ReagentPrepChefSdsIndexStoreProtocol):
    def __init__(
        self,
        *,
        cache_root: Path,
        fetcher: ReagentPrepChefSdsFetcherProtocol,
    ) -> None:
        self._cache_root = cache_root
        self._files_dir = cache_root / "files"
        self._index_path = cache_root / "index.json"
        self._fetcher = fetcher
        self._lock = asyncio.Lock()
        self._index = self._load_index()

    async def ensure(self, *, hazard: HazardEntry, allow_fetch: bool = True) -> HazardSdsData:
        async with self._lock:
            entry = self._index.entries.get(hazard.key)
            if entry and self._file_exists(entry) and _entry_is_complete(entry):
                return _entry_to_data(entry)

        if not allow_fetch:
            raise not_found("SDS", hazard.key)

        fetched = await self._fetcher.fetch(hazard=hazard)
        entry = self._store_fetch(hazard=hazard, fetched=fetched)
        return _entry_to_data(entry)

    def is_cached_complete(self, *, hazard: HazardEntry) -> bool:
        entry = self._index.entries.get(hazard.key)
        if entry is None:
            return False
        if not self._file_exists(entry):
            return False
        return _entry_is_complete(entry)

    def get_cached(self, *, sds_ref: str) -> tuple[str, bytes, str]:
        entry = self._index.entries.get(sds_ref)
        if entry is None:
            entry = self._find_by_sds_ref(sds_ref)
        if entry is None:
            raise not_found("SDS", sds_ref)
        if not _is_pdf_entry(entry):
            raise not_found("SDS", sds_ref)
        path = self._files_dir / entry.file_name
        if not path.is_file():
            raise not_found("SDS", sds_ref)
        return (entry.file_name, path.read_bytes(), entry.media_type)

    def _file_exists(self, entry: _SdsIndexEntry) -> bool:
        if not _is_pdf_entry(entry):
            return False
        path = self._files_dir / entry.file_name
        return path.is_file()

    def _store_fetch(self, *, hazard: HazardEntry, fetched: SdsFetchResult) -> _SdsIndexEntry:
        self._cache_root.mkdir(parents=True, exist_ok=True)
        self._files_dir.mkdir(parents=True, exist_ok=True)

        existing = self._index.entries.get(hazard.key)
        extension = _extension_for_media_type(fetched.media_type)
        file_name = f"{fetched.sds_ref}{extension}"
        file_path = self._files_dir / file_name
        file_path.write_bytes(fetched.sds_bytes)

        sha256 = hashlib.sha256(fetched.sds_bytes).hexdigest()
        entry = _SdsIndexEntry(
            key=hazard.key,
            display_name=hazard.display_name,
            sds_ref=fetched.sds_ref,
            file_name=file_name,
            media_type=fetched.media_type,
            sha256=sha256,
            source_url=fetched.source_url,
            retrieved_at=datetime.now(tz=timezone.utc).isoformat(),
            hazard_codes=list(fetched.hazard_codes),
            pictograms=list(fetched.pictograms),
            signal_word=fetched.signal_word,
            clp_bands=[_band_to_model(band) for band in fetched.clp_bands],
            incompatibilities=list(fetched.incompatibilities),
            exothermicity=fetched.exothermicity,
            reaction_notes=list(fetched.reaction_notes),
            density_g_ml=float(fetched.density_g_ml) if fetched.density_g_ml is not None else None,
            sources=list(fetched.sources),
        )

        self._index.entries[hazard.key] = entry
        if hazard.key != entry.sds_ref:
            self._index.entries[entry.sds_ref] = entry
        self._persist_index()
        if existing is not None and existing.file_name != entry.file_name:
            previous_path = self._files_dir / existing.file_name
            if previous_path.is_file():
                previous_path.unlink()
        return entry

    def _load_index(self) -> _SdsIndex:
        if not self._index_path.is_file():
            return _SdsIndex()
        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
            return _SdsIndex.model_validate(payload)
        except (
            OSError,
            ValidationError,
            json.JSONDecodeError,
        ) as exc:
            raise validation_error("SDS-index kunde inte läsas.") from exc

    def _persist_index(self) -> None:
        payload = self._index.model_dump(mode="json")
        self._index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _find_by_sds_ref(self, sds_ref: str) -> _SdsIndexEntry | None:
        for entry in self._index.entries.values():
            if entry.sds_ref == sds_ref:
                return entry
        return None


def _entry_to_data(entry: _SdsIndexEntry) -> HazardSdsData:
    return HazardSdsData(
        sds_ref=entry.sds_ref,
        hazard_codes=tuple(entry.hazard_codes),
        pictograms=tuple(entry.pictograms),
        signal_word=_normalize_signal_word(entry.signal_word),
        clp_bands=tuple(_model_to_band(item) for item in entry.clp_bands),
        incompatibilities=tuple(entry.incompatibilities),
        exothermicity=entry.exothermicity,
        reaction_notes=tuple(entry.reaction_notes),
        sources=tuple(entry.sources),
    )


def _normalize_signal_word(value: str | None) -> Literal["danger", "warning"] | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized == "danger":
        return "danger"
    if normalized == "warning":
        return "warning"
    return None


def _band_to_model(band: ClpBand) -> _ClpBandModel:
    return _ClpBandModel(
        min_molarity=float(band.min_molarity) if band.min_molarity is not None else None,
        max_molarity=float(band.max_molarity) if band.max_molarity is not None else None,
        hazard_codes=list(band.hazard_codes),
        pictograms=list(band.pictograms),
        signal_word=band.signal_word,
        notes=list(band.notes),
    )


def _model_to_band(model: _ClpBandModel) -> ClpBand:
    min_molarity = model.min_molarity
    max_molarity = model.max_molarity
    return ClpBand(
        min_molarity=None if min_molarity is None else Decimal(str(min_molarity)),
        max_molarity=None if max_molarity is None else Decimal(str(max_molarity)),
        hazard_codes=tuple(model.hazard_codes),
        pictograms=tuple(model.pictograms),
        signal_word=_normalize_signal_word(model.signal_word),
        notes=tuple(model.notes),
    )


def _entry_is_complete(entry: _SdsIndexEntry) -> bool:
    if not entry.clp_bands:
        return False
    if entry.density_g_ml is None:
        return False
    if not entry.incompatibilities and not entry.reaction_notes and entry.exothermicity is None:
        return False
    return True


def _extension_for_media_type(media_type: str) -> str:
    if media_type == "application/pdf":
        return ".pdf"
    if media_type == "application/json":
        return ".json"
    return ".bin"


def _is_pdf_entry(entry: _SdsIndexEntry) -> bool:
    return entry.media_type == "application/pdf"
