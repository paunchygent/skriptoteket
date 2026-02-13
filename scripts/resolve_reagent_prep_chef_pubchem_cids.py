from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx
from molmass import Formula

from scripts.pubchem_aliases_lib import normalize_formula_for_molmass
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.reagent_prep_chef.formulas import normalize_formula_key
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.hazards_store import (
    InMemoryReagentPrepChefHazardStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.pubchem_client import (
    PubChemClient,
    PubChemClientSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_query_variants import (
    dedupe_preserve_order,
    looks_like_formula,
)
from skriptoteket.observability.logging import configure_logging


@dataclass(frozen=True)
class ResolvedCid:
    hazard_key: str
    display_name: str
    cid: int
    title: str
    formula: str


@dataclass(frozen=True)
class Candidate:
    cid: int
    title: str
    formula: str


def _hazards_path() -> Path:
    from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef import hazards_store

    return Path(hazards_store.__file__).with_name("hazards.json")


def _extract_properties(payload: dict) -> list[dict]:
    table = payload.get("PropertyTable")
    if not isinstance(table, dict):
        return []
    props = table.get("Properties")
    if not isinstance(props, list):
        return []
    return [item for item in props if isinstance(item, dict)]


def _split_properties_payload(payload: dict) -> dict[int, dict]:
    mapping: dict[int, dict] = {}
    for props in _extract_properties(payload):
        cid = props.get("CID")
        if isinstance(cid, int):
            mapping[cid] = props
    return mapping


async def _fetch_properties_for_cids(
    *,
    pubchem: PubChemClient,
    cids: list[int],
    batch_size: int,
) -> dict[int, dict]:
    remaining = list(cids)
    current_batch = max(1, batch_size)
    results: dict[int, dict] = {}
    while remaining:
        batch = remaining[:current_batch]
        try:
            payload = await pubchem.fetch_properties_batch(
                cids=batch, properties=["Title", "MolecularFormula"]
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in {400, 414} and current_batch > 1:
                current_batch = max(1, current_batch // 2)
                continue
            raise
        results.update(_split_properties_payload(payload))
        remaining = remaining[current_batch:]
    return results


def _formula_counts(formula: str) -> dict[str, int]:
    comp = Formula(normalize_formula_for_molmass(formula)).composition().asdict()
    counts: dict[str, int] = {}
    for element, values in comp.items():
        count = int(values[0])
        counts[element] = count
    return counts


def _formula_equal(left: str, right: str) -> bool:
    try:
        return _formula_counts(left) == _formula_counts(right)
    except Exception:
        return False


def _formula_candidates(hazard) -> list[str]:
    raw_values = [hazard.key, *hazard.aliases]
    candidates: list[str] = []
    for value in raw_values:
        if not looks_like_formula(value):
            continue
        normalized = normalize_formula_key(value)
        if normalized:
            candidates.append(normalized)
        try:
            hill = Formula(normalize_formula_for_molmass(normalized)).formula
        except Exception:
            hill = None
        if hill:
            candidates.append(hill)
    return dedupe_preserve_order(candidates)


def _match_by_search_aliases(
    *,
    candidates: list[Candidate],
    search_aliases: tuple[str, ...],
) -> list[Candidate]:
    if not search_aliases:
        return []
    normalized = {alias.casefold() for alias in search_aliases if alias}
    if not normalized:
        return []
    matches: list[Candidate] = []
    for candidate in candidates:
        if candidate.title.casefold() in normalized:
            matches.append(candidate)
    return matches


async def _resolve_for_formula(
    *,
    pubchem: PubChemClient,
    formula: str,
    properties_cache: dict[int, dict],
    cache_lock: asyncio.Lock,
) -> list[Candidate]:
    cids = await pubchem.resolve_cids(queries=[formula], max_candidates=None)
    if not cids:
        return []
    missing: list[int] = []
    async with cache_lock:
        for cid in cids:
            if cid not in properties_cache:
                missing.append(cid)
    if missing:
        fetched = await _fetch_properties_for_cids(
            pubchem=pubchem,
            cids=missing,
            batch_size=50,
        )
        for cid, props in fetched.items():
            properties_cache[cid] = props
    candidates: list[Candidate] = []
    async with cache_lock:
        for cid in cids:
            props = properties_cache.get(cid)
            if not isinstance(props, dict):
                continue
            title = props.get("Title")
            mol_formula = props.get("MolecularFormula")
            if not isinstance(title, str) or not isinstance(mol_formula, str):
                continue
            if _formula_equal(mol_formula.strip(), formula):
                candidates.append(
                    Candidate(cid=cid, title=title.strip(), formula=mol_formula.strip())
                )
    return candidates


async def _resolve_for_name_queries(
    *,
    pubchem: PubChemClient,
    search_aliases: tuple[str, ...],
    formulas: list[str],
    properties_cache: dict[int, dict],
    cache_lock: asyncio.Lock,
) -> list[Candidate]:
    if not search_aliases:
        return []
    if not formulas:
        return []
    candidates: dict[int, Candidate] = {}
    for alias in search_aliases:
        alias = alias.strip()
        if not alias:
            continue
        cids = await pubchem.resolve_cids(queries=[alias], max_candidates=None)
        if not cids:
            continue
        missing: list[int] = []
        async with cache_lock:
            for cid in cids:
                if cid not in properties_cache:
                    missing.append(cid)
        if missing:
            fetched = await _fetch_properties_for_cids(
                pubchem=pubchem,
                cids=missing,
                batch_size=50,
            )
            for cid, props in fetched.items():
                properties_cache[cid] = props
        async with cache_lock:
            for cid in cids:
                props = properties_cache.get(cid)
                if not isinstance(props, dict):
                    continue
                title = props.get("Title")
                mol_formula = props.get("MolecularFormula")
                if not isinstance(title, str) or not isinstance(mol_formula, str):
                    continue
                if not any(_formula_equal(mol_formula.strip(), formula) for formula in formulas):
                    continue
                candidates[cid] = Candidate(
                    cid=cid,
                    title=title.strip(),
                    formula=mol_formula.strip(),
                )
    return list(candidates.values())


async def _resolve_hazard(
    *,
    pubchem: PubChemClient,
    hazard,
    properties_cache: dict[int, dict],
    cache_lock: asyncio.Lock,
    semaphore: asyncio.Semaphore,
) -> tuple[str, dict]:
    async with semaphore:
        formulas = _formula_candidates(hazard)
        if not formulas:
            return (
                hazard.key,
                {
                    "status": "no_formula",
                    "display_name": hazard.display_name,
                    "formulas": [],
                },
            )
        all_candidates: list[Candidate] = []
        errors: list[str] = []
        for formula in formulas:
            try:
                candidates = await _resolve_for_formula(
                    pubchem=pubchem,
                    formula=formula,
                    properties_cache=properties_cache,
                    cache_lock=cache_lock,
                )
                all_candidates.extend(candidates)
            except httpx.HTTPError as exc:
                errors.append(f"{formula}: {exc}")
                continue
        if not all_candidates and hazard.search_aliases:
            try:
                all_candidates.extend(
                    await _resolve_for_name_queries(
                        pubchem=pubchem,
                        search_aliases=hazard.search_aliases,
                        formulas=formulas,
                        properties_cache=properties_cache,
                        cache_lock=cache_lock,
                    )
                )
            except httpx.HTTPError as exc:
                errors.append(f"search_aliases: {exc}")
        unique = {candidate.cid: candidate for candidate in all_candidates}
        name_matches = _match_by_search_aliases(
            candidates=list(unique.values()),
            search_aliases=hazard.search_aliases,
        )
        if len(name_matches) == 1:
            candidate = name_matches[0]
            return (
                hazard.key,
                {
                    "status": "resolved",
                    "display_name": hazard.display_name,
                    "cid": candidate.cid,
                    "title": candidate.title,
                    "formula": candidate.formula,
                    "formulas": formulas,
                    "matched_search_alias": candidate.title,
                },
            )
        if errors and not unique:
            return (
                hazard.key,
                {
                    "status": "error",
                    "display_name": hazard.display_name,
                    "formulas": formulas,
                    "errors": errors,
                },
            )
        if len(unique) == 1:
            candidate = next(iter(unique.values()))
            return (
                hazard.key,
                {
                    "status": "resolved",
                    "display_name": hazard.display_name,
                    "cid": candidate.cid,
                    "title": candidate.title,
                    "formula": candidate.formula,
                    "formulas": formulas,
                },
            )
        if not unique:
            return (
                hazard.key,
                {
                    "status": "not_found",
                    "display_name": hazard.display_name,
                    "formulas": formulas,
                    "errors": errors,
                },
            )
        return (
            hazard.key,
            {
                "status": "ambiguous",
                "display_name": hazard.display_name,
                "formulas": formulas,
                "errors": errors,
                "matched_search_aliases": [candidate.title for candidate in name_matches],
                "candidates": [
                    {
                        "cid": candidate.cid,
                        "title": candidate.title,
                        "formula": candidate.formula,
                    }
                    for candidate in unique.values()
                ],
            },
        )


async def _main_async(args: argparse.Namespace) -> int:
    settings = Settings()
    configure_logging(
        service_name=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    hazards_store = InMemoryReagentPrepChefHazardStore(hazards_path=_hazards_path())
    hazards = [hazard for hazard in hazards_store.list_all() if hazard.pubchem_cid is None]
    if args.only:
        wanted = set(args.only)
        hazards = [hazard for hazard in hazards if hazard.key in wanted]
    if args.limit:
        hazards = hazards[: args.limit]
    if not hazards:
        print("No hazards selected.")
        return 0

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

    results: dict[str, dict] = {}
    properties_cache: dict[int, dict] = {}
    cache_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(max(1, args.concurrency))
    try:
        tasks = [
            _resolve_hazard(
                pubchem=pubchem,
                hazard=hazard,
                properties_cache=properties_cache,
                cache_lock=cache_lock,
                semaphore=semaphore,
            )
            for hazard in hazards
        ]
        for task in asyncio.as_completed(tasks):
            key, payload = await task
            results[key] = payload
            status = payload.get("status")
            print(f"{status} {key}")
    finally:
        await pubchem.close()

    resolved = {
        key: payload for key, payload in results.items() if payload.get("status") == "resolved"
    }
    report = {
        "resolved_count": len(resolved),
        "total": len(results),
        "results": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote report: {args.report}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", default=[], help="Hazard key.")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".artifacts/pubchem-cid-resolve/report.json"),
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main_async(args)))


if __name__ == "__main__":
    main()
