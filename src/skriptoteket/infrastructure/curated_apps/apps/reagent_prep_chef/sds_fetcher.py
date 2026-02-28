"""PubChem-backed SDS fetch pipeline for Reagent Prep Chef.

Fetches an SDS PDF candidate (via provider registry) and derives structured signals:
GHS snapshot, chemistry heuristics, density, and concentration-dependent CLP bands.

PR-0062: supports best-effort outcomes by returning the best partial candidate when no
fully complete derivation is available. Strict callers must enforce completeness in the
SDS index store (e.g. export paths).
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from decimal import Decimal

import httpx
import structlog

from skriptoteket.domain.curated_apps.reagent_prep_chef.formulas import molar_mass_g_mol
from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    ClpBand,
    HazardEntry,
    SdsFetchResult,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.pubchem_client import (
    AsyncClientProtocol,
    PubChemClientProtocol,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_curated_meta_store import (
    CuratedSdsMetaStore,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher_settings import (
    ProgressReporter,
    SdsFetcherSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_density_g_ml,
    extract_density_g_ml_from_sds_text,
    extract_pubchem_ghs,
    extract_pubchem_nonhazardous,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_fetcher import (
    SdsPdfDocument,
    SdsPdfFetcher,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_providers import (
    SdsPdfProviderContext,
    SdsPdfProviderRegistry,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_query_variants import (
    dedupe_preserve_order,
    extract_autocomplete_terms,
    looks_like_formula,
    normalize_formula_variants,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_result_builder import (
    GhsSnapshot,
    build_clp_bands,
    merge_heuristics,
    merge_pdf_ghs,
)

logger = structlog.get_logger(__name__)

PARTIAL_SDS_BEST_EFFORT_REASON = "SDS saknas: ingen komplett SDS-data för {formula}."


def _has_heuristics(
    *, incompatibilities: list[str], exothermicity: object, reaction_notes: list[str]
) -> bool:
    return bool(incompatibilities) or bool(reaction_notes) or exothermicity is not None


def _is_complete_result(result: SdsFetchResult) -> bool:
    return (
        bool(result.clp_bands)
        and result.density_g_ml is not None
        and _has_heuristics(
            incompatibilities=list(result.incompatibilities),
            exothermicity=result.exothermicity,
            reaction_notes=list(result.reaction_notes),
        )
    )


def _candidate_score(result: SdsFetchResult) -> int:
    """Score best-effort results; higher means preferred."""
    score = 0
    if result.clp_bands:
        score += 4
    if result.density_g_ml is not None:
        score += 2
    if _has_heuristics(
        incompatibilities=list(result.incompatibilities),
        exothermicity=result.exothermicity,
        reaction_notes=list(result.reaction_notes),
    ):
        score += 1
    return score


def _best_effort_failure_details(
    *,
    formula: str,
    attempted_cids: list[int],
    best_partial: SdsFetchResult | None,
) -> dict[str, object]:
    details: dict[str, object] = {
        "formula": formula,
        "attempted_cids": attempted_cids,
    }
    if best_partial is None:
        return details

    missing: list[str] = []
    if not best_partial.clp_bands:
        missing.append("clp_bands")
    if best_partial.density_g_ml is None:
        missing.append("density_g_ml")
    if not _has_heuristics(
        incompatibilities=list(best_partial.incompatibilities),
        exothermicity=best_partial.exothermicity,
        reaction_notes=list(best_partial.reaction_notes),
    ):
        missing.append("heuristics")

    details["best_partial_missing"] = missing
    details["best_partial_source_url"] = best_partial.source_url
    return details


def _select_density_g_ml(
    *,
    pubchem_density_g_ml: Decimal | None,
    pdf_density_g_ml: Decimal | None,
) -> tuple[Decimal | None, str]:
    if pdf_density_g_ml is not None:
        return (pdf_density_g_ml, "pdf")
    if pubchem_density_g_ml is not None:
        return (pubchem_density_g_ml, "pubchem")
    return (None, "missing")


class PubChemSdsFetcher:
    def __init__(
        self,
        *,
        pubchem: PubChemClientProtocol,
        settings: SdsFetcherSettings,
        progress: ProgressReporter | None = None,
        sds_http: AsyncClientProtocol | None = None,
        pdf_provider_registry: SdsPdfProviderRegistry | None = None,
        curated_meta_store: CuratedSdsMetaStore | None = None,
    ) -> None:
        self._pubchem = pubchem
        self._settings = settings
        self._progress = progress
        self._pdf_fetcher = SdsPdfFetcher(
            settings=settings,
            progress=progress,
            http_client=sds_http,
            provider_registry=pdf_provider_registry,
        )
        self._curated_meta_store = curated_meta_store

    async def fetch(self, *, hazard: HazardEntry) -> SdsFetchResult:
        log = logger.bind(hazard_key=hazard.key, hazard_name=hazard.display_name)
        self._emit(log, "fetch_start")
        candidates: list[int] = []
        allow_fallback = hazard.pubchem_cid is None
        if hazard.pubchem_cid is not None:
            candidates = [hazard.pubchem_cid]
            self._emit(log, "resolve_cid_fixed", cid=hazard.pubchem_cid)
        else:
            if self._settings.require_pubchem_cid:
                self._emit(log, "resolve_cid_missing")
                raise validation_error(f"SDS saknas: saknar PubChem CID för {hazard.key}.")
            candidates = await self._resolve_cid_candidates(
                hazard,
                log=log,
                max_candidates=self._settings.cid_candidate_limit,
            )
        if not candidates:
            candidates = await self._resolve_cid_candidates(
                hazard,
                log=log,
                use_autocomplete=True,
                max_candidates=self._settings.cid_candidate_limit,
            )
        if not candidates:
            self._emit(log, "resolve_cid_missing")
            raise validation_error(f"SDS saknas: kunde inte hitta PubChem CID för {hazard.key}.")

        best_partial: SdsFetchResult | None = None
        best_partial_score = -1
        last_attempted: list[int] = []

        def _consider(result: SdsFetchResult) -> SdsFetchResult | None:
            nonlocal best_partial, best_partial_score
            if _is_complete_result(result):
                return result
            score = _candidate_score(result)
            if score > best_partial_score:
                best_partial = result
                best_partial_score = score
            return None

        for cid in candidates:
            last_attempted.append(cid)
            result = await self._fetch_for_cid(hazard=hazard, cid=cid, log=log)
            if result is None:
                continue
            complete = _consider(result)
            if complete is not None:
                return complete

        if not allow_fallback:
            self._emit(log, "fetch_failed_fixed_cid", cid=hazard.pubchem_cid)
            if best_partial is not None:
                return best_partial
            raise validation_error(
                PARTIAL_SDS_BEST_EFFORT_REASON.format(formula=hazard.key),
                details=_best_effort_failure_details(
                    formula=hazard.key,
                    attempted_cids=last_attempted,
                    best_partial=best_partial,
                ),
            )

        if len(candidates) >= self._settings.cid_candidate_limit:
            self._emit(log, "resolve_cid_expand", attempted=len(last_attempted))
            expanded_candidates = await self._resolve_cid_candidates(
                hazard,
                log=log,
                exclude_cids=last_attempted,
                max_candidates=None,
            )
            for cid in expanded_candidates:
                last_attempted.append(cid)
                result = await self._fetch_for_cid(hazard=hazard, cid=cid, log=log)
                if result is None:
                    continue
                complete = _consider(result)
                if complete is not None:
                    return complete

        fallback_candidates = await self._resolve_cid_candidates(
            hazard,
            log=log,
            use_autocomplete=True,
            exclude_cids=last_attempted,
            max_candidates=self._settings.cid_candidate_limit,
        )
        for cid in fallback_candidates:
            last_attempted.append(cid)
            result = await self._fetch_for_cid(hazard=hazard, cid=cid, log=log)
            if result is None:
                continue
            complete = _consider(result)
            if complete is not None:
                return complete

        self._emit(log, "fetch_failed_no_hazard_codes", cids=last_attempted)
        if best_partial is not None:
            return best_partial
        raise validation_error(
            PARTIAL_SDS_BEST_EFFORT_REASON.format(formula=hazard.key),
            details=_best_effort_failure_details(
                formula=hazard.key,
                attempted_cids=last_attempted,
                best_partial=best_partial,
            ),
        )

    async def _resolve_cid_candidates(
        self,
        hazard: HazardEntry,
        *,
        log: structlog.stdlib.BoundLogger,
        use_autocomplete: bool = False,
        exclude_cids: list[int] | None = None,
        max_candidates: int | None,
    ) -> list[int]:
        base_queries = [*hazard.search_aliases, hazard.key, *hazard.aliases]
        expanded_queries: list[str] = []
        for query in base_queries:
            if looks_like_formula(query):
                expanded_queries.extend(normalize_formula_variants(query))
        queries = dedupe_preserve_order([*base_queries, *expanded_queries])
        self._emit(log, "resolve_cid_start", queries=queries)
        if use_autocomplete:
            autocomplete_queries = await self._expand_queries_with_autocomplete(
                queries=queries,
                log=log,
            )
            if autocomplete_queries:
                self._emit(log, "resolve_cid_autocomplete", queries=autocomplete_queries)
                queries = autocomplete_queries
        candidates = await self._pubchem.resolve_cids(
            queries=queries, max_candidates=max_candidates
        )
        if exclude_cids:
            candidates = [cid for cid in candidates if cid not in exclude_cids]
        self._emit(log, "resolve_cid_candidates", cids=candidates)
        return candidates

    async def _expand_queries_with_autocomplete(
        self,
        *,
        queries: list[str],
        log: structlog.stdlib.BoundLogger,
    ) -> list[str]:
        suggestions: list[str] = []
        for query in queries:
            if not query:
                continue
            if looks_like_formula(query):
                continue
            try:
                terms = await self._pubchem.autocomplete_compound(
                    query=query,
                    max_terms=self._settings.autocomplete_limit,
                )
            except httpx.HTTPError as exc:
                self._emit(
                    log,
                    "autocomplete_error",
                    query=query,
                    error=str(exc),
                )
                continue
            suggestions.extend(terms)
        expanded: list[str] = []
        for suggestion in dedupe_preserve_order(suggestions):
            expanded.extend(extract_autocomplete_terms(suggestion))
        return dedupe_preserve_order(expanded)

    async def _fetch_for_cid(
        self, *, hazard: HazardEntry, cid: int, log: structlog.stdlib.BoundLogger
    ) -> SdsFetchResult | None:
        curated_meta = None
        if self._curated_meta_store is not None:
            curated_meta = self._curated_meta_store.get(cid=cid)
        self._emit(log, "pubchem_fetch_start", cid=cid)
        lcss_payload = await self._fetch_lcss_payload(cid=cid, log=log)
        ghs = await self._resolve_ghs_snapshot(cid=cid, lcss_payload=lcss_payload, log=log)
        pdf_document = await self._fetch_pdf_document(
            hazard=hazard,
            cid=cid,
            lcss_payload=lcss_payload,
            log=log,
        )
        if pdf_document is None:
            self._emit(log, "candidate_missing_pdf", cid=cid)
            return None

        ghs = merge_pdf_ghs(snapshot=ghs, pdf_text=pdf_document.text)
        if not ghs.hazard_codes and not ghs.nonhazardous:
            self._emit(log, "candidate_no_pdf_hazard_codes", cid=cid)
            return None

        incompatibilities, exothermicity, reaction_notes = merge_heuristics(
            pdf_text=pdf_document.text,
        )
        if not _has_heuristics(
            incompatibilities=incompatibilities,
            exothermicity=exothermicity,
            reaction_notes=reaction_notes,
        ):
            self._emit(log, "candidate_missing_heuristics", cid=cid)

        used_curated_meta = False
        density_g_ml: Decimal | None = None
        if curated_meta is not None and curated_meta.density_g_ml is not None:
            density_g_ml = curated_meta.density_g_ml
            used_curated_meta = True
            self._emit(log, "density_from_curated", cid=cid)
        else:
            pubchem_density_g_ml = await self._fetch_density(cid=cid, log=log)
            pdf_density_g_ml = extract_density_g_ml_from_sds_text(pdf_document.text)
            density_g_ml, density_source = _select_density_g_ml(
                pubchem_density_g_ml=pubchem_density_g_ml,
                pdf_density_g_ml=pdf_density_g_ml,
            )
            if density_source == "pdf":
                self._emit(log, "density_from_pdf", cid=cid)
                if pubchem_density_g_ml is not None and pdf_density_g_ml is not None:
                    if pubchem_density_g_ml != pdf_density_g_ml:
                        self._emit(
                            log,
                            "density_overrode_pubchem",
                            cid=cid,
                            pubchem_density_g_ml=str(pubchem_density_g_ml),
                            pdf_density_g_ml=str(pdf_density_g_ml),
                        )
            elif density_source == "missing":
                self._emit(log, "candidate_missing_density", cid=cid)

        clp_bands: tuple[ClpBand, ...] = ()
        if curated_meta is not None and curated_meta.clp_bands:
            clp_bands = curated_meta.clp_bands
            used_curated_meta = True
            self._emit(log, "clp_bands_from_curated", cid=cid)
        elif density_g_ml is not None:
            parsed_bands = build_clp_bands(
                pdf_text=pdf_document.text,
                molar_mass=molar_mass_g_mol(formula_clean=hazard.key),
                density_g_ml=density_g_ml,
                snapshot=ghs,
                emit=lambda stage: self._emit(log, stage),
            )
            if parsed_bands is not None:
                clp_bands = parsed_bands

        sources = [*ghs.sources, pdf_document.source_url, "PubChem"]
        if used_curated_meta and curated_meta is not None and curated_meta.sources:
            sources.extend(curated_meta.sources)
        sources = list(dict.fromkeys(sources))

        return SdsFetchResult(
            sds_ref=hazard.sds_ref or hazard.key,
            sds_bytes=pdf_document.sds_bytes,
            media_type=pdf_document.media_type,
            source_url=pdf_document.source_url,
            hazard_codes=tuple(ghs.hazard_codes),
            pictograms=tuple(ghs.pictograms),
            signal_word=ghs.signal_word,
            clp_bands=clp_bands,
            incompatibilities=tuple(incompatibilities),
            exothermicity=exothermicity,
            reaction_notes=tuple(reaction_notes),
            density_g_ml=density_g_ml,
            sources=tuple(sources),
        )

    async def _fetch_lcss_payload(self, *, cid: int, log: structlog.stdlib.BoundLogger) -> dict:
        return await self._call_with_retry(
            log=log,
            stage="pubchem_lcss",
            call=lambda: self._pubchem.fetch_lcss(cid=cid),
        )

    async def _resolve_ghs_snapshot(
        self,
        *,
        cid: int,
        lcss_payload: dict,
        log: structlog.stdlib.BoundLogger,
    ) -> GhsSnapshot:
        hazard_codes, pictograms, signal_word = extract_pubchem_ghs(lcss_payload)
        nonhazardous = extract_pubchem_nonhazardous(lcss_payload)
        sources = [f"{self._pubchem.base_url}/rest/pug_view/data/compound/{cid}/JSON?toc=LCSS+TOC"]

        if not hazard_codes and not nonhazardous:
            ghs_payload = await self._fetch_heading_payload(
                cid=cid,
                heading="GHS Classification",
                stage="pubchem_ghs_heading",
                log=log,
            )
            if ghs_payload is not None:
                ghs_codes, ghs_pictograms, ghs_signal = extract_pubchem_ghs(ghs_payload)
                ghs_nonhazardous = extract_pubchem_nonhazardous(ghs_payload)
                hazard_codes = ghs_codes
                pictograms = sorted({*pictograms, *ghs_pictograms})
                signal_word = ghs_signal or signal_word
                nonhazardous = ghs_nonhazardous
                if hazard_codes or nonhazardous:
                    sources.append(
                        f"{self._pubchem.base_url}/rest/pug_view/data/compound/{cid}/JSON?heading=GHS+Classification"
                    )

        return GhsSnapshot(
            hazard_codes=hazard_codes,
            pictograms=pictograms,
            signal_word=signal_word,
            nonhazardous=nonhazardous,
            sources=sources,
        )

    async def _fetch_heading_payload(
        self,
        *,
        cid: int,
        heading: str,
        stage: str,
        log: structlog.stdlib.BoundLogger,
    ) -> dict | None:
        try:
            return await self._call_with_retry(
                log=log,
                stage=stage,
                call=lambda: self._pubchem.fetch_heading(cid=cid, heading=heading),
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                self._emit(log, f"{stage}_missing", cid=cid)
                return None
            raise

    async def _fetch_pdf_document(
        self,
        *,
        hazard: HazardEntry,
        cid: int,
        lcss_payload: dict,
        log: structlog.stdlib.BoundLogger,
    ) -> SdsPdfDocument | None:
        linkout_payload = await self._call_with_retry(
            log=log,
            stage="pubchem_linkout",
            call=lambda: self._pubchem.fetch_linkout(cid=cid),
        )
        safety_payload = await self._fetch_heading_payload(
            cid=cid,
            heading="Safety and Hazards",
            stage="pubchem_safety_heading",
            log=log,
        )
        context = SdsPdfProviderContext(
            hazard=hazard,
            cid=cid,
            lcss_payload=lcss_payload,
            linkout_payload=linkout_payload,
            safety_payload=safety_payload,
        )
        return await self._pdf_fetcher.fetch(context=context, log=log)

    async def _fetch_density(
        self, *, cid: int, log: structlog.stdlib.BoundLogger
    ) -> Decimal | None:
        density_payload = await self._fetch_heading_payload(
            cid=cid,
            heading="Density",
            stage="pubchem_density_heading",
            log=log,
        )
        if density_payload is None:
            return None
        return extract_density_g_ml(density_payload)

    async def _call_with_retry(
        self,
        *,
        log: structlog.stdlib.BoundLogger,
        stage: str,
        call: Callable[[], Awaitable[dict]],
    ) -> dict:
        attempts = max(self._settings.retry_attempts, 1)
        for attempt in range(1, attempts + 1):
            self._emit(log, f"{stage}_start", attempt=attempt, attempts=attempts)
            start = time.monotonic()
            try:
                result = await call()
            except httpx.HTTPError as exc:
                elapsed = time.monotonic() - start
                self._emit(
                    log,
                    f"{stage}_error",
                    attempt=attempt,
                    elapsed_seconds=round(elapsed, 2),
                    error=str(exc),
                )
                if attempt == attempts:
                    raise
                await self._backoff_sleep(attempt=attempt)
                continue
            elapsed = time.monotonic() - start
            self._emit(
                log,
                f"{stage}_done",
                attempt=attempt,
                elapsed_seconds=round(elapsed, 2),
            )
            return result
        raise validation_error("SDS saknas: kunde inte hämta PubChem-data.")

    async def _backoff_sleep(self, *, attempt: int) -> None:
        base = self._settings.retry_backoff_seconds
        max_sleep = self._settings.retry_backoff_max_seconds
        jitter = random.uniform(0.5, 1.5)
        delay = min(max_sleep, base * (2 ** (attempt - 1)) * jitter)
        await asyncio.sleep(delay)

    def _emit(
        self,
        log: structlog.stdlib.BoundLogger,
        stage: str,
        **payload: object,
    ) -> None:
        if self._progress is not None:
            self._progress(stage, payload)
            return
        log.info("sds_fetch_progress", stage=stage, **payload)
