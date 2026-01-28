from __future__ import annotations

import asyncio
from collections.abc import Iterable
from pathlib import Path

import typer

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import HazardEntry
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.hazards_store import (
    InMemoryReagentPrepChefHazardStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.pubchem_client import (
    PubChemClient,
    PubChemClientSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher import (
    PubChemSdsFetcher,
    SdsFetcherSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_index_store import (
    FileSystemReagentPrepChefSdsIndexStore,
)


def seed_sds_cache(
    only: list[str] = typer.Option(
        [],
        "--only",
        help="Filter by formula key (repeatable). Defaults to all hazards.",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        min=1,
        help="Optional cap for how many hazards to fetch (after filtering).",
    ),
    fail_fast: bool = typer.Option(
        True,
        help="Stop at first failure (recommended for CI).",
    ),
) -> None:
    """Fetch and cache SDS data for curated Reagent Prep Chef hazards."""
    asyncio.run(_seed_sds_cache_async(only=only, limit=limit, fail_fast=fail_fast))


async def _seed_sds_cache_async(*, only: list[str], limit: int | None, fail_fast: bool) -> None:
    settings = Settings()

    hazards_path = _hazards_path()
    hazards_store = InMemoryReagentPrepChefHazardStore(hazards_path=hazards_path)
    hazards = _filter_hazards(hazards_store.list_all(), only=only)
    if limit is not None:
        hazards = hazards[:limit]

    cache_root = settings.SDS_CACHE_ROOT or (settings.ARTIFACTS_ROOT / "sds-cache")
    pubchem = PubChemClient(
        settings=PubChemClientSettings(
            base_url=settings.PUBCHEM_BASE_URL,
            timeout_seconds=settings.PUBCHEM_TIMEOUT_SECONDS,
            user_agent=settings.SDS_FETCH_USER_AGENT,
        )
    )
    fetcher = PubChemSdsFetcher(
        pubchem=pubchem,
        settings=SdsFetcherSettings(
            timeout_seconds=settings.SDS_FETCH_TIMEOUT_SECONDS,
            user_agent=settings.SDS_FETCH_USER_AGENT,
        ),
    )
    index = FileSystemReagentPrepChefSdsIndexStore(cache_root=cache_root, fetcher=fetcher)

    failures = 0
    for hazard in hazards:
        try:
            await index.ensure(hazard=hazard)
            typer.echo(f"OK {hazard.key} → cached")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            typer.echo(f"FAIL {hazard.key}: {exc}")
            if fail_fast:
                await pubchem.close()
                raise SystemExit(1) from exc

    await pubchem.close()
    if failures:
        raise SystemExit(1)


def _hazards_path() -> Path:
    from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import hazards_store

    return Path(hazards_store.__file__).with_name("hazards.json")


def _filter_hazards(hazards: Iterable[HazardEntry], *, only: list[str]) -> list[HazardEntry]:
    if not only:
        return list(hazards)
    normalized = {value.strip() for value in only if value.strip()}
    return [hazard for hazard in hazards if hazard.key in normalized]
