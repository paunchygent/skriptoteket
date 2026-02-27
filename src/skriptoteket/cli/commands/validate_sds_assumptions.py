"""Validate SDS fetch assumptions against real Reagent Prep Chef data.

This command is a data-first helper for PR-0062 (Riskbedömning best-effort contract).
It samples hazards from an existing `seed_sds_cache --report` JSON report and then probes
the SDS fetch pipeline to build a small "truthy" failure taxonomy:

- No PDF candidate found (`candidate_missing_pdf`)
- PDF found but missing heuristics/density/CLP bands (partial candidates)

The output report is intended for rapid iteration: validate assumptions early against
real shapes and avoid building large contract changes on toy examples.

Related code:
  - `src/skriptoteket/cli/commands/seed_sds_cache.py` (produces the input report)
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_fetcher.py`
  - `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_index_store.py`
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import typer

from skriptoteket.config import Settings
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

APP_ID = "chemistry.reagent_prep_chef"
DerivedStatus = Literal["ok", "partial", "fail"]


def validate_sds_assumptions(
    report_path: Path = typer.Option(
        Path(".artifacts/sds-cache/full-report.json"),
        "--report",
        help="Path to a JSON report from `seed_sds_cache --report ...`.",
    ),
    out_path: Path = typer.Option(
        Path(".artifacts/sds-cache/assumption-validation.json"),
        "--out",
        help="Where to write the diagnostic JSON report.",
    ),
    cache_root: Path = typer.Option(
        Path(".artifacts/sds-cache-assumptions"),
        "--cache-root",
        help="Cache root used during probing (gitignored by default).",
    ),
    only: list[str] = typer.Option(
        [],
        "--only",
        help=(
            "Probe only these hazard keys (repeatable). Overrides sampling from the seed report."
        ),
    ),
    sample_ok: int = typer.Option(
        3,
        "--sample-ok",
        min=0,
        help="How many OK hazards from the report to probe (0 = skip).",
    ),
    sample_fail: int = typer.Option(
        12,
        "--sample-fail",
        min=1,
        help="How many FAIL hazards from the report to probe.",
    ),
    sample_seed: int = typer.Option(
        42,
        "--sample-seed",
        min=0,
        help="Deterministic seed for sampling.",
    ),
    require_cid: bool = typer.Option(
        True,
        "--require-cid/--no-require-cid",
        help="Require PubChem CID for every hazard (recommended for deterministic probing).",
    ),
) -> None:
    """Probe a small sample of hazards and emit a failure taxonomy report."""
    asyncio.run(
        _validate_sds_assumptions_async(
            report_path=report_path,
            out_path=out_path,
            cache_root=cache_root,
            only=only,
            sample_ok=sample_ok,
            sample_fail=sample_fail,
            sample_seed=sample_seed,
            require_cid=require_cid,
        )
    )


async def _validate_sds_assumptions_async(
    *,
    report_path: Path,
    out_path: Path,
    cache_root: Path,
    only: list[str],
    sample_ok: int,
    sample_fail: int,
    sample_seed: int,
    require_cid: bool,
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
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    logging.getLogger("pypdf._reader").setLevel(logging.ERROR)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = list(payload.get("results") or [])
    ok_keys = [item["key"] for item in results if item.get("status") == "ok"]
    fail_keys = [item["key"] for item in results if item.get("status") != "ok"]
    report_generated_at = payload.get("generated_at")

    hazards_path = _hazards_path()
    hazards_store = InMemoryReagentPrepChefHazardStore(hazards_path=hazards_path)
    hazards_by_key = {hazard.key: hazard for hazard in hazards_store.list_all()}

    selection: dict[str, list[str]]
    if only:
        normalized = [value.strip() for value in only if value.strip()]
        deduped = list(dict.fromkeys(normalized))
        selection = {"ok": [], "fail": []}
        for key in deduped:
            status = _status_from_report(key=key, results=results)
            if status == "ok":
                selection["ok"].append(key)
            else:
                selection["fail"].append(key)
    else:
        selection = _select_sample(
            ok_keys=ok_keys,
            fail_keys=fail_keys,
            sample_ok=sample_ok,
            sample_fail=sample_fail,
            sample_seed=sample_seed,
        )
    typer.echo(
        f"Selected hazards: ok={len(selection['ok'])} fail={len(selection['fail'])} "
        f"(seed={sample_seed})"
    )

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

    current_key: str | None = None
    events_by_key: dict[str, list[dict[str, Any]]] = {}

    def _progress(stage: str, event_payload: dict[str, object]) -> None:
        nonlocal current_key
        if current_key is None:
            return
        if current_key not in events_by_key:
            events_by_key[current_key] = []
        events_by_key[current_key].append({"stage": stage, "payload": dict(event_payload)})

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
            progress=_progress,
            curated_store=curated_store,
        ),
        curated_meta_store=curated_meta_store,
        progress=_progress,
    )
    index = FileSystemReagentPrepChefSdsIndexStore(cache_root=cache_root, fetcher=fetcher)

    hazard_reports: list[dict[str, Any]] = []

    try:
        for key in [*selection["ok"], *selection["fail"]]:
            hazard = hazards_by_key.get(key)
            if hazard is None:
                hazard_reports.append(
                    {
                        "key": key,
                        "status_from_report": _status_from_report(key=key, results=results),
                        "probe_status": "fail",
                        "derived_status": "fail",
                        "error": "Missing hazard in hazards.json",
                        "candidate_stage_counts": {},
                    }
                )
                continue

            current_key = key
            events_by_key[key] = []
            start = time.monotonic()
            probe_status: Literal["ok", "fail"]
            error: str | None = None
            try:
                await index.ensure(hazard=hazard, allow_fetch=True)
                probe_status = "ok"
            except Exception as exc:  # noqa: BLE001
                probe_status = "fail"
                error = str(exc).strip() or type(exc).__name__
            finally:
                elapsed_seconds = round(time.monotonic() - start, 2)
                current_key = None

            candidate_counts = _candidate_stage_counts(events_by_key[key])
            derived_status = _derive_status(
                probe_status=probe_status, candidate_counts=candidate_counts
            )
            hazard_reports.append(
                {
                    "key": hazard.key,
                    "display_name": hazard.display_name,
                    "pubchem_cid": hazard.pubchem_cid,
                    "status_from_report": _status_from_report(key=key, results=results),
                    "probe_status": probe_status,
                    "derived_status": derived_status,
                    "elapsed_seconds": elapsed_seconds,
                    "error": error,
                    "candidate_stage_counts": candidate_counts,
                }
            )

            typer.echo(
                f"{hazard.key}: report={_status_from_report(key=key, results=results)} "
                f"probe={probe_status} derived={derived_status} "
                f"candidates={dict(candidate_counts) or '{}'}"
            )
    finally:
        await pubchem.close()

    aggregate = _build_aggregate(hazard_reports)
    out_payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "source": {
            "app_id": APP_ID,
            "report_path": str(report_path),
            "report_generated_at": report_generated_at,
            "report_summary": payload.get("summary"),
            "cache_root": str(cache_root),
        },
        "selection": selection,
        "aggregate": aggregate,
        "hazards": hazard_reports,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    typer.echo(
        "Aggregate derived_status: "
        + " ".join(f"{key}={value}" for key, value in aggregate["derived_status_counts"].items())
    )
    typer.echo(f"Wrote: {out_path}")


def _hazards_path() -> Path:
    from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import hazards_store

    return Path(hazards_store.__file__).with_name("hazards.json")


def _status_from_report(*, key: str, results: list[dict[str, Any]]) -> str | None:
    for item in results:
        if item.get("key") == key:
            return str(item.get("status"))
    return None


def _select_sample(
    *,
    ok_keys: list[str],
    fail_keys: list[str],
    sample_ok: int,
    sample_fail: int,
    sample_seed: int,
) -> dict[str, list[str]]:
    ok_selected: list[str] = []
    fail_selected: list[str] = []

    fixed_ok = ["C3H6O", "Al", "AlCl3·6H2O"]
    for key in fixed_ok:
        if len(ok_selected) >= sample_ok:
            break
        if key in ok_keys and key not in ok_selected:
            ok_selected.append(key)
    if len(ok_selected) < sample_ok:
        rng = random.Random(sample_seed)
        remaining = [key for key in ok_keys if key not in ok_selected]
        rng.shuffle(remaining)
        ok_selected.extend(remaining[: max(0, sample_ok - len(ok_selected))])

    fixed_fail = [
        "NaCl",
        "CH3COOH",
        "C2H6O",
        "(NH4)2SO4",
        "Al2(SO4)3·18H2O",
        "Cu",
    ]
    for key in fixed_fail:
        if len(fail_selected) >= sample_fail:
            break
        if key in fail_keys and key not in fail_selected:
            fail_selected.append(key)

    def pick_first(predicate) -> None:
        for key in fail_keys:
            if len(fail_selected) >= sample_fail:
                return
            if key in fail_selected:
                continue
            if predicate(key):
                fail_selected.append(key)
                return

    pick_first(lambda key: "(" in key)
    pick_first(lambda key: "·" in key)
    pick_first(lambda key: key.startswith("C") and key not in ok_keys)
    element_re = re.compile(r"^[A-Z][a-z]?$")
    pick_first(lambda key: element_re.match(key) is not None)

    if len(fail_selected) < sample_fail:
        rng = random.Random(sample_seed)
        remaining = [key for key in fail_keys if key not in fail_selected]
        rng.shuffle(remaining)
        fail_selected.extend(remaining[: max(0, sample_fail - len(fail_selected))])

    return {"ok": ok_selected, "fail": fail_selected[:sample_fail]}


def _candidate_stage_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for event in events:
        stage = str(event.get("stage") or "")
        if stage.startswith("candidate_"):
            counts[stage] += 1
    return dict(counts)


def _derive_status(*, probe_status: str, candidate_counts: dict[str, int]) -> DerivedStatus:
    if probe_status == "ok":
        return "ok"
    has_pdf_candidate = any(
        key in candidate_counts
        for key in (
            "candidate_no_pdf_hazard_codes",
            "candidate_missing_heuristics",
            "candidate_missing_density",
            "candidate_missing_clp_bands",
        )
    )
    return "partial" if has_pdf_candidate else "fail"


def _build_aggregate(hazard_reports: list[dict[str, Any]]) -> dict[str, Any]:
    derived = Counter(item.get("derived_status") for item in hazard_reports)
    stage_counts: Counter[str] = Counter()
    for item in hazard_reports:
        if item.get("probe_status") != "fail":
            continue
        stage_counts.update(item.get("candidate_stage_counts") or {})
    top_stages = [{"stage": stage, "count": count} for stage, count in stage_counts.most_common(15)]
    return {
        "derived_status_counts": dict(derived),
        "top_candidate_stages_on_fail": top_stages,
    }
