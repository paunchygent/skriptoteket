from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from molmass import Formula

from skriptoteket.config import Settings
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
class HazardRecord:
    key: str
    display_name: str
    aliases: list[str]
    pubchem_cid: int | None
    payload: dict[str, object]


@dataclass(frozen=True)
class CandidateTitle:
    cid: int
    title: str
    formula: str


@dataclass(frozen=True)
class CacheState:
    cid_cache: dict[str, list[int]]
    property_cache: dict[int, dict]
    cid_lock: asyncio.Lock
    property_lock: asyncio.Lock


def load_hazards(path: Path) -> list[HazardRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SystemExit("hazards.json must be a JSON list")
    records: list[HazardRecord] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("key", "")).strip()
        display_name = str(entry.get("display_name", "")).strip()
        aliases = entry.get("aliases", [])
        pubchem_cid = entry.get("pubchem_cid")
        if pubchem_cid is not None:
            if isinstance(pubchem_cid, bool) or not isinstance(pubchem_cid, int):
                raise SystemExit(f"pubchem_cid must be an int for {key}")
            if pubchem_cid <= 0:
                raise SystemExit(f"pubchem_cid must be positive for {key}")
        if not key or not display_name:
            continue
        alias_list = [str(value).strip() for value in aliases if isinstance(value, str)]
        records.append(
            HazardRecord(
                key=key,
                display_name=display_name,
                aliases=alias_list,
                pubchem_cid=pubchem_cid,
                payload=entry,
            )
        )
    return records


def normalize_formula_for_molmass(formula: str) -> str:
    return formula.replace("·", ".").replace("*", ".").replace(" ", "")


def _formula_candidates(record: HazardRecord) -> list[str]:
    raw = [record.key, *record.aliases]
    formulas = [value for value in raw if looks_like_formula(value)]
    return dedupe_preserve_order(formulas)


def _hill_formula(formula: str) -> str | None:
    try:
        normalized = normalize_formula_for_molmass(formula)
        return Formula(normalized).formula
    except Exception:
        return None


def unique_hill_formulas(record: HazardRecord) -> list[str]:
    formulas: list[str] = []
    for value in _formula_candidates(record):
        hill = _hill_formula(value)
        if hill:
            formulas.append(hill)
    return dedupe_preserve_order(formulas)


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
        if not isinstance(cid, int):
            continue
        mapping[cid] = {"PropertyTable": {"Properties": [props]}}
    return mapping


async def _fetch_properties_for_cids(
    *,
    pubchem: PubChemClient,
    cids: list[int],
    properties: list[str],
    batch_size: int,
) -> dict[int, dict]:
    remaining = list(cids)
    current_batch = max(1, batch_size)
    results: dict[int, dict] = {}
    while remaining:
        batch = remaining[:current_batch]
        try:
            payload = await pubchem.fetch_properties_batch(cids=batch, properties=properties)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in {400, 414} and current_batch > 1:
                current_batch = max(1, current_batch // 2)
                continue
            raise
        results.update(_split_properties_payload(payload))
        remaining = remaining[current_batch:]
    return results


async def _resolve_titles_for_formula(
    *,
    pubchem: PubChemClient,
    formula: str,
    cache: CacheState,
    batch_size: int,
) -> list[CandidateTitle]:
    async with cache.cid_lock:
        cids = cache.cid_cache.get(formula)
    if cids is None:
        cids = await pubchem.resolve_cids(queries=[formula], max_candidates=None)
        async with cache.cid_lock:
            cache.cid_cache.setdefault(formula, cids)

    candidates: list[CandidateTitle] = []
    async with cache.property_lock:
        missing = [cid for cid in cids if cid not in cache.property_cache]
    if missing:
        fetched = await _fetch_properties_for_cids(
            pubchem=pubchem,
            cids=missing,
            properties=["Title", "MolecularFormula"],
            batch_size=batch_size,
        )
        async with cache.property_lock:
            for cid, payload in fetched.items():
                cache.property_cache.setdefault(cid, payload)

    async with cache.property_lock:
        payloads = {cid: cache.property_cache.get(cid) for cid in cids}

    for cid, payload in payloads.items():
        if not payload:
            continue
        for props in _extract_properties(payload):
            title = props.get("Title")
            mol_formula = props.get("MolecularFormula")
            if not isinstance(title, str) or not isinstance(mol_formula, str):
                continue
            if mol_formula.strip() != formula:
                continue
            candidates.append(CandidateTitle(cid=cid, title=title.strip(), formula=mol_formula))
    return candidates


async def _resolve_titles_for_cids(
    *,
    pubchem: PubChemClient,
    cids: list[int],
    cache: CacheState,
    batch_size: int,
) -> list[CandidateTitle]:
    candidates: list[CandidateTitle] = []
    if not cids:
        return candidates
    async with cache.property_lock:
        missing = [cid for cid in cids if cid not in cache.property_cache]
    if missing:
        fetched = await _fetch_properties_for_cids(
            pubchem=pubchem,
            cids=missing,
            properties=["Title", "MolecularFormula"],
            batch_size=batch_size,
        )
        async with cache.property_lock:
            for cid, payload in fetched.items():
                cache.property_cache.setdefault(cid, payload)
    async with cache.property_lock:
        payloads = {cid: cache.property_cache.get(cid) for cid in cids}
    for cid, payload in payloads.items():
        if not payload:
            continue
        for props in _extract_properties(payload):
            title = props.get("Title")
            mol_formula = props.get("MolecularFormula")
            if not isinstance(title, str) or not isinstance(mol_formula, str):
                continue
            candidates.append(
                CandidateTitle(cid=cid, title=title.strip(), formula=mol_formula.strip())
            )
    return candidates


async def _process_record(
    *,
    record: HazardRecord,
    pubchem: PubChemClient,
    cache: CacheState,
    batch_size: int,
    require_cid: bool,
) -> dict[str, object]:
    formulas = unique_hill_formulas(record)
    all_candidates: list[CandidateTitle] = []
    if record.pubchem_cid is None and require_cid:
        return {
            "key": record.key,
            "display_name": record.display_name,
            "formulas": formulas,
            "candidates": [],
            "titles": [],
            "status": "missing_cid",
            "selected": None,
        }
    if record.pubchem_cid is not None:
        all_candidates = await _resolve_titles_for_cids(
            pubchem=pubchem,
            cids=[record.pubchem_cid],
            cache=cache,
            batch_size=batch_size,
        )
    else:
        for formula in formulas:
            all_candidates.extend(
                await _resolve_titles_for_formula(
                    pubchem=pubchem,
                    formula=formula,
                    cache=cache,
                    batch_size=batch_size,
                )
            )
    unique_by_cid: dict[int, CandidateTitle] = {}
    for candidate in all_candidates:
        unique_by_cid.setdefault(candidate.cid, candidate)
    candidates = list(unique_by_cid.values())
    titles = sorted({candidate.title for candidate in candidates})

    status = None
    selected = None
    if record.pubchem_cid is not None:
        if not candidates:
            status = "missing"
        else:
            candidate = candidates[0]
            if formulas and candidate.formula not in formulas:
                status = "cid_mismatch"
            else:
                status = "resolved"
                selected = candidate.title
    elif len(titles) == 1:
        status = "resolved"
        selected = titles[0]
    elif not titles:
        status = "missing"
        selected = None
    else:
        status = "ambiguous"
        selected = None

    return {
        "key": record.key,
        "display_name": record.display_name,
        "formulas": formulas,
        "pubchem_cid": record.pubchem_cid,
        "candidates": [
            {"cid": candidate.cid, "title": candidate.title, "formula": candidate.formula}
            for candidate in candidates
        ],
        "titles": titles,
        "status": status,
        "selected": selected,
    }


async def run_alias_generation(
    *,
    hazards: list[HazardRecord],
    hazards_path: Path,
    output_path: Path,
    write: bool,
    allow_partial: bool,
    concurrency: int,
    batch_size: int,
    progress_path: Path | None,
    checkpoint_every: int,
    require_cid: bool,
) -> dict[str, object]:
    settings = Settings()
    configure_logging(
        service_name=settings.SERVICE_NAME,
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
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

    logger = logging.getLogger(__name__)
    cache = CacheState(
        cid_cache={},
        property_cache={},
        cid_lock=asyncio.Lock(),
        property_lock=asyncio.Lock(),
    )
    results: list[dict[str, object] | None] = [None for _ in hazards]
    progress_file = None
    if progress_path is not None:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_file = progress_path.open("w", encoding="utf-8")

    try:
        semaphore = asyncio.Semaphore(max(1, concurrency))
        total = len(hazards)
        summary = {
            "resolved": 0,
            "missing": 0,
            "ambiguous": 0,
            "missing_cid": 0,
            "cid_mismatch": 0,
            "total": total,
        }
        started_at = time.monotonic()

        async def _run_record(index: int, record: HazardRecord) -> tuple[int, dict[str, object]]:
            async with semaphore:
                return index, await _process_record(
                    record=record,
                    pubchem=pubchem,
                    cache=cache,
                    batch_size=batch_size,
                    require_cid=require_cid,
                )

        tasks = [asyncio.create_task(_run_record(i, record)) for i, record in enumerate(hazards)]
        processed = 0
        for future in asyncio.as_completed(tasks):
            index, result = await future
            results[index] = result
            processed += 1
            status = result.get("status")
            if status in summary:
                summary[status] += 1
            elapsed = time.monotonic() - started_at
            avg = elapsed / processed if processed else 0.0
            eta = avg * (total - processed)
            progress_entry = {
                "index": processed,
                "total": total,
                "key": result.get("key"),
                "status": status,
                "resolved": summary["resolved"],
                "missing": summary["missing"],
                "ambiguous": summary["ambiguous"],
                "missing_cid": summary["missing_cid"],
                "cid_mismatch": summary["cid_mismatch"],
                "elapsed_seconds": round(elapsed, 2),
                "eta_seconds": round(eta, 2),
            }
            if progress_file is not None:
                progress_file.write(json.dumps(progress_entry, ensure_ascii=False) + "\n")
                progress_file.flush()
            if checkpoint_every > 0 and processed % checkpoint_every == 0:
                partial = [item for item in results if item is not None]
                checkpoint_path = output_path.with_suffix(".partial.json")
                checkpoint_path.write_text(
                    json.dumps(
                        {"summary": summary, "results": partial}, ensure_ascii=False, indent=2
                    ),
                    encoding="utf-8",
                )
            if processed % max(1, checkpoint_every) == 0:
                logger.info(
                    "Alias progress %s/%s (resolved=%s missing=%s ambiguous=%s missing_cid=%s cid_mismatch=%s eta=%.1fs)",
                    processed,
                    total,
                    summary["resolved"],
                    summary["missing"],
                    summary["ambiguous"],
                    summary["missing_cid"],
                    summary["cid_mismatch"],
                    eta,
                )
    finally:
        await pubchem.close()
        if progress_file is not None:
            progress_file.close()

    if any(item is None for item in results):
        raise SystemExit("Alias generation did not complete for all hazards.")
    final_results = [item for item in results if item is not None]
    summary = {
        "resolved": len([item for item in final_results if item["status"] == "resolved"]),
        "missing": len([item for item in final_results if item["status"] == "missing"]),
        "ambiguous": len([item for item in final_results if item["status"] == "ambiguous"]),
        "missing_cid": len([item for item in final_results if item["status"] == "missing_cid"]),
        "cid_mismatch": len([item for item in final_results if item["status"] == "cid_mismatch"]),
        "total": len(final_results),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"summary": summary, "results": final_results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote report: {output_path}")
    print(f"Summary: {summary}")

    if not write:
        return {"summary": summary, "results": final_results}

    if not allow_partial and (
        summary["missing"]
        or summary["ambiguous"]
        or summary["missing_cid"]
        or summary["cid_mismatch"]
    ):
        raise SystemExit("Refusing to write hazards.json with missing/ambiguous entries.")

    updated_payload: list[dict[str, object]] = []
    by_key = {item["key"]: item for item in final_results}
    for record in hazards:
        entry = dict(record.payload)
        result = by_key.get(record.key)
        if result and result["status"] == "resolved":
            entry["search_aliases"] = [result["selected"]]
        else:
            entry["search_aliases"] = []
        updated_payload.append(entry)

    hazards_path.write_text(
        json.dumps(updated_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Updated hazards.json with search_aliases.")
    return {"summary": summary, "results": final_results}
