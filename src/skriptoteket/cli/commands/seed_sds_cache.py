from __future__ import annotations

import asyncio
import json
import logging
import random
from collections.abc import Iterable
from datetime import datetime, timezone
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
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_curated_meta_store import (
    CuratedSdsMetaStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher import (
    PubChemSdsFetcher,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher_settings import (
    SdsFetcherSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_index_store import (
    FileSystemReagentPrepChefSdsIndexStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_providers import (
    CuratedSdsLinkoutStore,
    build_sds_pdf_provider_registry,
)
from skriptoteket.observability.logging import configure_logging


def seed_sds_cache(
    only: list[str] = typer.Option(
        [],
        "--only",
        help="Filter by formula key (repeatable). Defaults to all hazards.",
    ),
    only_missing: bool = typer.Option(
        False,
        "--only-missing",
        help="Only fetch hazards missing or incomplete in the SDS cache.",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        min=1,
        help="Optional cap for how many hazards to fetch (after filtering).",
    ),
    sample: int | None = typer.Option(
        None,
        "--sample",
        min=1,
        help="Random sample size (after filtering).",
    ),
    sample_seed: int = typer.Option(
        42,
        "--sample-seed",
        min=0,
        help="Seed for deterministic sampling.",
    ),
    concurrency: int | None = typer.Option(
        None,
        "--concurrency",
        min=1,
        help="Max concurrent SDS fetches (defaults to SDS_FETCH_CONCURRENCY).",
    ),
    require_cid: bool = typer.Option(
        True,
        "--require-cid/--no-require-cid",
        help="Require PubChem CID for every hazard (no fallback resolution).",
    ),
    fail_fast: bool = typer.Option(
        True,
        help="Stop at first failure (recommended for CI).",
    ),
    report_path: Path | None = typer.Option(
        None,
        "--report",
        help="Write a JSON report summary to this path.",
    ),
) -> None:
    """Fetch and cache SDS data for curated Reagent Prep Chef hazards."""
    asyncio.run(
        _seed_sds_cache_async(
            only=only,
            only_missing=only_missing,
            limit=limit,
            sample=sample,
            sample_seed=sample_seed,
            concurrency=concurrency,
            require_cid=require_cid,
            fail_fast=fail_fast,
            report_path=report_path,
        )
    )


async def _seed_sds_cache_async(
    *,
    only: list[str],
    only_missing: bool,
    limit: int | None,
    sample: int | None,
    sample_seed: int,
    concurrency: int | None,
    require_cid: bool,
    fail_fast: bool,
    report_path: Path | None,
) -> None:
    settings = Settings()
    configure_logging(
        service_name=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    hazards_path = _hazards_path()
    hazards_store = InMemoryReagentPrepChefHazardStore(hazards_path=hazards_path)

    cache_root = settings.SDS_CACHE_ROOT or (settings.ARTIFACTS_ROOT / "sds-cache")
    max_concurrency = concurrency or settings.SDS_FETCH_CONCURRENCY
    if max_concurrency < 1:
        max_concurrency = 1
    pubchem = PubChemClient(
        settings=PubChemClientSettings(
            base_url=settings.PUBCHEM_BASE_URL,
            timeout_seconds=settings.SDS_FETCH_TIMEOUT_SECONDS,
            user_agent=settings.SDS_FETCH_USER_AGENT,
            listkey_max_wait_seconds=settings.SDS_FETCH_LISTKEY_MAX_SECONDS,
            listkey_poll_interval_seconds=settings.SDS_FETCH_LISTKEY_POLL_SECONDS,
            resolve_retry_attempts=settings.SDS_FETCH_RETRY_ATTEMPTS,
            resolve_retry_backoff_seconds=settings.SDS_FETCH_RETRY_BACKOFF_SECONDS,
            resolve_retry_backoff_max_seconds=settings.SDS_FETCH_RETRY_BACKOFF_MAX_SECONDS,
            rate_limit_per_second=settings.PUBCHEM_RATE_LIMIT_PER_SECOND,
            max_in_flight=settings.PUBCHEM_MAX_IN_FLIGHT,
            throttle_yellow_delay_seconds=settings.PUBCHEM_THROTTLE_YELLOW_DELAY_SECONDS,
            throttle_red_delay_seconds=settings.PUBCHEM_THROTTLE_RED_DELAY_SECONDS,
        )
    )
    curated_store = None
    if settings.SDS_CURATED_LINKOUTS_PATH is not None:
        curated_store = CuratedSdsLinkoutStore(path=settings.SDS_CURATED_LINKOUTS_PATH)
    curated_meta_store = None
    if settings.SDS_CURATED_META_PATH is not None:
        curated_meta_store = CuratedSdsMetaStore(path=settings.SDS_CURATED_META_PATH)
    fetcher = PubChemSdsFetcher(
        pubchem=pubchem,
        settings=SdsFetcherSettings(
            timeout_seconds=settings.SDS_FETCH_TIMEOUT_SECONDS,
            user_agent=settings.SDS_FETCH_USER_AGENT,
            retry_attempts=settings.SDS_FETCH_RETRY_ATTEMPTS,
            retry_backoff_seconds=settings.SDS_FETCH_RETRY_BACKOFF_SECONDS,
            retry_backoff_max_seconds=settings.SDS_FETCH_RETRY_BACKOFF_MAX_SECONDS,
            require_pubchem_cid=require_cid,
            cid_candidate_limit=settings.SDS_FETCH_CID_CANDIDATE_LIMIT,
            autocomplete_limit=settings.SDS_FETCH_AUTOCOMPLETE_LIMIT,
        ),
        pdf_provider_registry=build_sds_pdf_provider_registry(
            progress=_progress_reporter,
            curated_store=curated_store,
        ),
        curated_meta_store=curated_meta_store,
        progress=_progress_reporter,
    )
    index = FileSystemReagentPrepChefSdsIndexStore(cache_root=cache_root, fetcher=fetcher)
    hazards = _filter_hazards(hazards_store.list_all(), only=only)
    if only_missing:
        hazards = [hazard for hazard in hazards if not index.is_cached_complete(hazard=hazard)]
    if limit is not None:
        hazards = hazards[:limit]
    if sample is not None:
        if sample < len(hazards):
            rng = random.Random(sample_seed)
            hazards = rng.sample(hazards, sample)

    if not hazards:
        typer.echo("No hazards selected for SDS fetch.")
        return

    failures = 0
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks: list[asyncio.Task[tuple[HazardEntry, Exception | None]]] = []
    first_failure: Exception | None = None
    results: list[dict[str, object]] = []

    _emit_selection_summary(hazards)

    async def _process(hazard: HazardEntry) -> tuple[HazardEntry, Exception | None]:
        async with semaphore:
            try:
                await index.ensure(hazard=hazard)
                typer.echo(f"OK {hazard.key} → cached")
                return (hazard, None)
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"FAIL {hazard.key}: {_format_exception(exc)}")
                return (hazard, exc)

    for hazard in hazards:
        tasks.append(asyncio.create_task(_process(hazard)))

    try:
        for task in asyncio.as_completed(tasks):
            hazard, exc = await task
            results.append(_build_result(hazard=hazard, exc=exc))
            if exc is None:
                continue
            failures += 1
            if fail_fast and first_failure is None:
                first_failure = exc
                break

        if first_failure is not None:
            for pending in tasks:
                if not pending.done():
                    pending.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise SystemExit(1) from first_failure

        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await pubchem.close()

    _emit_summary(results, report_path=report_path)

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


def _emit_selection_summary(hazards: list[HazardEntry]) -> None:
    keys = [hazard.key for hazard in hazards]
    preview = ", ".join(keys[:10])
    suffix = f" (+{len(keys) - 10} more)" if len(keys) > 10 else ""
    if keys:
        typer.echo(f"Selected hazards ({len(keys)}): {preview}{suffix}")


def _build_result(
    *,
    hazard: HazardEntry,
    exc: Exception | None,
) -> dict[str, object]:
    reason = None if exc is None else _format_exception(exc)
    return {
        "key": hazard.key,
        "display_name": hazard.display_name,
        "status": "ok" if exc is None else "fail",
        "reason": reason,
    }


def _emit_summary(results: list[dict[str, object]], *, report_path: Path | None) -> None:
    total = len(results)
    ok_count = sum(1 for item in results if item["status"] == "ok")
    fail_count = total - ok_count
    typer.echo(f"Summary: ok={ok_count} fail={fail_count} total={total}")

    failures: dict[str, int] = {}
    for item in results:
        if item["status"] != "fail":
            continue
        reason = str(item.get("reason") or "Unknown")
        failures[reason] = failures.get(reason, 0) + 1

    for reason, count in sorted(failures.items(), key=lambda entry: (-entry[1], entry[0])):
        typer.echo(f"Fail reason ({count}): {reason}")

    if report_path is None:
        return
    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "summary": {
            "ok": ok_count,
            "fail": fail_count,
            "total": total,
        },
        "results": results,
    }
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _progress_reporter(stage: str, payload: dict[str, object]) -> None:
    parts = [f"{key}={_format_progress_value(value)}" for key, value in payload.items()]
    message = " ".join(part for part in parts if part)
    typer.echo(f"[{stage}] {message}".strip())


def _format_progress_value(value: object) -> str:
    if isinstance(value, list):
        preview = value[:5]
        suffix = f"...(+{len(value) - 5})" if len(value) > 5 else ""
        return f"{preview}{suffix}"
    text = str(value)
    return text.replace("\n", " ").strip()


def _format_exception(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return type(exc).__name__
