from __future__ import annotations

from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    HazardEntry,
    SdsFetchResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_index_store import (
    FileSystemReagentPrepChefSdsIndexStore,
)


class FakeFetcher:
    def __init__(self, *, result: SdsFetchResult) -> None:
        self._result = result
        self.calls: list[str] = []

    async def fetch(self, *, hazard: HazardEntry) -> SdsFetchResult:
        self.calls.append(hazard.key)
        return self._result


def _partial_pdf_result(*, sds_ref: str) -> SdsFetchResult:
    return SdsFetchResult(
        sds_ref=sds_ref,
        sds_bytes=b"%PDF-1.4\npartial\n",
        media_type="application/pdf",
        source_url="https://example.test/sds.pdf",
        hazard_codes=("H302",),
        pictograms=("GHS07",),
        signal_word="warning",
        clp_bands=(),
        incompatibilities=(),
        exothermicity=None,
        reaction_notes=(),
        density_g_ml=None,
        sources=("PubChem",),
    )


@pytest.mark.asyncio
async def test_ensure_best_effort_caches_partial_entry(tmp_path: Path) -> None:
    hazard = HazardEntry(key="NaCl", display_name="Salt")
    fetched = _partial_pdf_result(sds_ref="pubchem_1")
    fetcher = FakeFetcher(result=fetched)
    store = FileSystemReagentPrepChefSdsIndexStore(cache_root=tmp_path / "cache", fetcher=fetcher)

    sds_data = await store.ensure(hazard=hazard, allow_fetch=True, require_complete=False)
    assert sds_data.sds_ref == "pubchem_1"
    assert sds_data.density_g_ml is None
    assert sds_data.clp_bands == ()
    assert sds_data.incompatibilities == ()
    assert sds_data.exothermicity is None
    assert sds_data.reaction_notes == ()

    file_path = tmp_path / "cache" / "files" / "pubchem_1.pdf"
    assert file_path.is_file()
    assert store.is_cached_complete(hazard=hazard) is False
    assert fetcher.calls == ["NaCl"]

    file_name, blob, media_type = store.get_cached(sds_ref="pubchem_1")
    assert file_name == "pubchem_1.pdf"
    assert blob == fetched.sds_bytes
    assert media_type == "application/pdf"

    cached_offline = await store.ensure(hazard=hazard, allow_fetch=False, require_complete=False)
    assert cached_offline.sds_ref == "pubchem_1"
    assert fetcher.calls == ["NaCl"]


@pytest.mark.asyncio
async def test_ensure_strict_raises_but_leaves_pdf_cached(tmp_path: Path) -> None:
    hazard = HazardEntry(key="NaCl", display_name="Salt")
    fetched = _partial_pdf_result(sds_ref="pubchem_1")
    fetcher = FakeFetcher(result=fetched)
    store = FileSystemReagentPrepChefSdsIndexStore(cache_root=tmp_path / "cache", fetcher=fetcher)

    with pytest.raises(DomainError) as excinfo:
        await store.ensure(hazard=hazard, allow_fetch=True, require_complete=True)

    error = excinfo.value
    assert error.code == ErrorCode.VALIDATION_ERROR
    assert error.details.get("formula") == "NaCl"
    assert error.details.get("missing") == ["clp_bands", "density_g_ml", "heuristics"]

    file_name, blob, media_type = store.get_cached(sds_ref="pubchem_1")
    assert file_name == "pubchem_1.pdf"
    assert blob == fetched.sds_bytes
    assert media_type == "application/pdf"
    assert store.is_cached_complete(hazard=hazard) is False


@pytest.mark.asyncio
async def test_ensure_strict_offline_raises_validation_error_for_cached_partial(
    tmp_path: Path,
) -> None:
    hazard = HazardEntry(key="NaCl", display_name="Salt")
    fetched = _partial_pdf_result(sds_ref="pubchem_1")
    fetcher = FakeFetcher(result=fetched)
    store = FileSystemReagentPrepChefSdsIndexStore(cache_root=tmp_path / "cache", fetcher=fetcher)

    await store.ensure(hazard=hazard, allow_fetch=True, require_complete=False)

    with pytest.raises(DomainError) as excinfo:
        await store.ensure(hazard=hazard, allow_fetch=False, require_complete=True)

    error = excinfo.value
    assert error.code == ErrorCode.VALIDATION_ERROR
    assert error.details.get("missing") == ["clp_bands", "density_g_ml", "heuristics"]
    assert fetcher.calls == ["NaCl"]
