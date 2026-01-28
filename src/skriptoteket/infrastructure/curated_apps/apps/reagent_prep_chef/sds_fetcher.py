from __future__ import annotations

import re
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse

import httpx

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    ClpBand,
    HazardEntry,
    SdsFetchResult,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.pubchem_client import (
    PubChemClient,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_candidate_urls,
    extract_hazard_codes_from_text,
    extract_pdf_text,
    extract_pictograms_from_text,
    extract_pubchem_ghs,
    extract_signal_word_from_text,
    parse_sds_heuristics_from_text,
)


@dataclass(frozen=True, slots=True)
class SdsFetcherSettings:
    timeout_seconds: float
    user_agent: str
    sds_required: bool = True


class PubChemSdsFetcher:
    def __init__(self, *, pubchem: PubChemClient, settings: SdsFetcherSettings) -> None:
        self._pubchem = pubchem
        self._settings = settings

    async def fetch(self, *, hazard: HazardEntry) -> SdsFetchResult:
        cid = await self._resolve_cid(hazard)
        if cid is None:
            raise validation_error(f"SDS saknas: kunde inte hitta PubChem CID för {hazard.key}.")

        pug_view = await self._pubchem.fetch_pug_view(cid=cid)
        linkout = await self._pubchem.fetch_linkout(cid=cid)

        candidate_urls = self._collect_candidate_urls(pug_view, linkout, hazard)

        pubchem_hazard_codes, pubchem_pictograms, pubchem_signal = extract_pubchem_ghs(pug_view)

        async for sds_bytes, media_type, source_url in self._iter_pdf_candidates(candidate_urls):
            sds_text = extract_pdf_text(sds_bytes)
            incompatibilities, exothermicity, reaction_notes = parse_sds_heuristics_from_text(
                sds_text
            )
            if not incompatibilities and not reaction_notes and exothermicity is None:
                continue

            hazard_codes = pubchem_hazard_codes or extract_hazard_codes_from_text(sds_text)
            if not hazard_codes:
                continue

            pictograms = pubchem_pictograms or extract_pictograms_from_text(sds_text)
            signal_word = pubchem_signal or extract_signal_word_from_text(sds_text)

            clp_bands = (
                ClpBand(
                    min_molarity=None,
                    max_molarity=None,
                    hazard_codes=tuple(hazard_codes),
                    pictograms=tuple(pictograms),
                    signal_word=signal_word,
                    notes=(),
                ),
            )

            return SdsFetchResult(
                sds_ref=hazard.sds_ref or hazard.key,
                sds_bytes=sds_bytes,
                media_type=media_type,
                source_url=source_url,
                hazard_codes=tuple(hazard_codes),
                pictograms=tuple(pictograms),
                signal_word=signal_word,
                clp_bands=clp_bands,
                incompatibilities=tuple(incompatibilities),
                exothermicity=exothermicity,
                reaction_notes=tuple(reaction_notes),
                sources=(source_url, "PubChem"),
            )

        if not pubchem_hazard_codes:
            raise validation_error(f"SDS saknas: ingen GHS-klassning för {hazard.key}.")
        raise validation_error(f"SDS saknas: ingen reaktivitetsdata för {hazard.key}.")

    async def _resolve_cid(self, hazard: HazardEntry) -> int | None:
        queries = [hazard.key, hazard.display_name, *hazard.aliases]
        return await self._pubchem.resolve_cid(queries=queries)

    def _collect_candidate_urls(
        self, pug_view: dict, linkout: dict, hazard: HazardEntry
    ) -> list[str]:
        urls = set(extract_candidate_urls(pug_view))
        urls.update(extract_candidate_urls(linkout))
        urls.update(self._search_queries(hazard))
        ranked = sorted(urls, key=_score_url, reverse=True)
        return ranked

    def _search_queries(self, hazard: HazardEntry) -> Iterable[str]:
        terms = [hazard.display_name, hazard.key]
        for term in terms:
            if not term:
                continue
            encoded = quote_plus(f"{term} SDS pdf")
            yield f"https://duckduckgo.com/html/?q={encoded}"

    async def _iter_pdf_candidates(self, urls: list[str]) -> AsyncIterator[tuple[bytes, str, str]]:
        async with httpx.AsyncClient(
            timeout=self._settings.timeout_seconds,
            headers={"User-Agent": self._settings.user_agent},
            follow_redirects=True,
        ) as client:
            index = 0
            seen: set[str] = set()
            while index < len(urls):
                url = urls[index]
                index += 1
                if url in seen:
                    continue
                seen.add(url)
                if "duckduckgo.com/html" in url:
                    urls_from_search = await self._parse_search_results(client=client, url=url)
                    urls.extend(urls_from_search)
                    continue
                try:
                    response = await client.get(url)
                except httpx.HTTPError:
                    continue
                if response.status_code >= 400:
                    continue
                content = response.content
                media_type = response.headers.get("content-type", "").split(";")[0]
                if _is_pdf(content, media_type):
                    yield (content, media_type or "application/pdf", url)

    async def _parse_search_results(self, *, client: httpx.AsyncClient, url: str) -> list[str]:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError:
            return []
        html = response.text
        links = re.findall(r"href=\"(https?://[^\"]+)\"", html)
        filtered = [link for link in links if _score_url(link) > 0]
        return filtered[:20]


def _is_pdf(content: bytes, media_type: str) -> bool:
    if media_type.lower() == "application/pdf":
        return True
    return content.startswith(b"%PDF")


def _score_url(url: str) -> int:
    lowered = url.lower()
    score = 0
    if "sds" in lowered or "msds" in lowered:
        score += 5
    if lowered.endswith(".pdf"):
        score += 4
    if "safety-data-sheet" in lowered:
        score += 4
    if "safety" in lowered and "sheet" in lowered:
        score += 2
    parsed = urlparse(url)
    if parsed.path.endswith(".pdf"):
        score += 2
    return score
