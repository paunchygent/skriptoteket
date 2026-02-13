from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import structlog

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import HazardEntry
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher_settings import (
    ProgressReporter,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_candidate_urls,
)


@dataclass(frozen=True, slots=True)
class SdsPdfCandidate:
    url: str
    label: str | None
    source: str
    score_bias: int = 0


@dataclass(frozen=True, slots=True)
class SdsPdfProviderContext:
    hazard: HazardEntry
    cid: int
    lcss_payload: dict
    linkout_payload: dict | None
    safety_payload: dict | None


class SdsPdfProviderProtocol(Protocol):
    name: str

    async def collect_candidates(
        self,
        *,
        context: SdsPdfProviderContext,
        log: structlog.stdlib.BoundLogger,
    ) -> list[SdsPdfCandidate]: ...


class CuratedSdsLinkoutStore:
    def __init__(self, *, path: Path) -> None:
        self._path = path
        self._entries = self._load()

    def _load(self) -> dict[str, list[dict] | list[str]]:
        if not self._path.is_file():
            return {}
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        entries = payload.get("entries")
        if not isinstance(entries, dict):
            return {}
        return entries

    def get_urls(self, *, cid: int) -> list[str]:
        items = self._entries.get(str(cid)) or []
        urls: list[str] = []
        for item in items:
            url: str | None = None
            if isinstance(item, dict):
                value = item.get("url")
                if isinstance(value, str):
                    url = value
            elif isinstance(item, str):
                url = item
            if url:
                urls.append(url)
        return urls


class CuratedSdsPdfProvider:
    name = "curated_linkouts"

    def __init__(self, *, store: CuratedSdsLinkoutStore) -> None:
        self._store = store

    async def collect_candidates(
        self,
        *,
        context: SdsPdfProviderContext,
        log: structlog.stdlib.BoundLogger,
    ) -> list[SdsPdfCandidate]:
        urls = self._store.get_urls(cid=context.cid)
        return [
            SdsPdfCandidate(
                url=url,
                label="curated linkout",
                source=self.name,
                score_bias=100,
            )
            for url in urls
        ]


class PubChemLinkOutProvider:
    name = "pubchem_linkout"

    async def collect_candidates(
        self,
        *,
        context: SdsPdfProviderContext,
        log: structlog.stdlib.BoundLogger,
    ) -> list[SdsPdfCandidate]:
        payload = context.linkout_payload or {}
        return _extract_linkout_candidates(payload=payload, source=self.name)


class PubChemSafetyUrlProvider:
    name = "pubchem_safety_urls"

    async def collect_candidates(
        self,
        *,
        context: SdsPdfProviderContext,
        log: structlog.stdlib.BoundLogger,
    ) -> list[SdsPdfCandidate]:
        if context.safety_payload is None:
            return []
        return _extract_payload_urls(
            payload=context.safety_payload,
            source=self.name,
        )


class PubChemLcssUrlProvider:
    name = "pubchem_lcss_urls"

    async def collect_candidates(
        self,
        *,
        context: SdsPdfProviderContext,
        log: structlog.stdlib.BoundLogger,
    ) -> list[SdsPdfCandidate]:
        return _extract_payload_urls(
            payload=context.lcss_payload,
            source=self.name,
        )


class SdsPdfProviderRegistry:
    def __init__(
        self,
        *,
        providers: list[SdsPdfProviderProtocol],
        progress: ProgressReporter | None = None,
    ) -> None:
        self._providers = providers
        self._progress = progress

    @classmethod
    def default(
        cls,
        *,
        progress: ProgressReporter | None = None,
        curated_store: CuratedSdsLinkoutStore | None = None,
    ) -> SdsPdfProviderRegistry:
        providers: list[SdsPdfProviderProtocol] = []
        if curated_store is not None:
            providers.append(CuratedSdsPdfProvider(store=curated_store))
        return cls(
            providers=[
                *providers,
                PubChemLinkOutProvider(),
                PubChemSafetyUrlProvider(),
                PubChemLcssUrlProvider(),
            ],
            progress=progress,
        )

    async def collect_candidates(
        self,
        *,
        context: SdsPdfProviderContext,
        log: structlog.stdlib.BoundLogger,
    ) -> list[SdsPdfCandidate]:
        combined: list[SdsPdfCandidate] = []
        seen: set[str] = set()

        for provider in self._providers:
            self._emit(log, "sds_provider_start", provider=provider.name)
            try:
                candidates = await provider.collect_candidates(context=context, log=log)
            except Exception as exc:  # noqa: BLE001
                self._emit(
                    log,
                    "sds_provider_error",
                    provider=provider.name,
                    error=str(exc),
                )
                continue
            self._emit(
                log,
                "sds_provider_done",
                provider=provider.name,
                count=len(candidates),
            )
            for candidate in candidates:
                url = candidate.url.strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                combined.append(candidate)

        if not combined:
            self._emit(log, "sds_provider_candidates_missing")
        else:
            self._emit(log, "sds_provider_candidates", count=len(combined))

        return combined

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


def build_sds_pdf_provider_registry(
    *,
    progress: ProgressReporter | None = None,
    curated_store: CuratedSdsLinkoutStore | None = None,
) -> SdsPdfProviderRegistry:
    providers: list[SdsPdfProviderProtocol] = []
    if curated_store:
        providers.append(CuratedSdsPdfProvider(store=curated_store))
    providers.extend(
        [
            PubChemLinkOutProvider(),
            PubChemSafetyUrlProvider(),
            PubChemLcssUrlProvider(),
        ]
    )
    return SdsPdfProviderRegistry(
        providers=providers,
        progress=progress,
    )


def _extract_linkout_candidates(
    *,
    payload: dict,
    source: str,
) -> list[SdsPdfCandidate]:
    linkout = payload.get("Linkout")
    if not isinstance(linkout, dict):
        return []
    obj_urls = linkout.get("ObjUrl")
    if not isinstance(obj_urls, list):
        return []
    candidates: list[SdsPdfCandidate] = []
    preferred: list[SdsPdfCandidate] = []
    for entry in obj_urls:
        if not isinstance(entry, dict):
            continue
        url = entry.get("Url")
        if not isinstance(url, str):
            continue
        label_parts: list[str] = []
        link_name = entry.get("LinkName")
        if isinstance(link_name, str):
            label_parts.append(link_name)
        for field in ("SubjectType", "Category", "Attribute"):
            values = entry.get(field)
            if isinstance(values, list):
                label_parts.extend([value for value in values if isinstance(value, str)])
        provider = entry.get("Provider")
        if isinstance(provider, dict):
            provider_name = provider.get("Name")
            if isinstance(provider_name, str):
                label_parts.append(provider_name)
        label = " ".join(label_parts) if label_parts else None
        if not _is_http_url(url):
            continue
        label_text = (label or "").lower()
        is_sds_label = _label_mentions_sds(label_text)
        if not is_sds_label and not is_possible_pdf_url(url):
            continue
        candidate = SdsPdfCandidate(url=url, label=label, source=source)
        candidates.append(candidate)
        if is_sds_label:
            preferred.append(candidate)
    return preferred or candidates


def _extract_payload_urls(*, payload: dict, source: str) -> list[SdsPdfCandidate]:
    urls = extract_candidate_urls(payload)
    candidates: list[SdsPdfCandidate] = []
    for url in urls:
        if not is_possible_pdf_url(url):
            continue
        candidates.append(SdsPdfCandidate(url=url, label=None, source=source))
    return candidates


def _is_http_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def is_possible_pdf_url(url: str) -> bool:
    """Cheap filter for PDF-like URLs before downloading."""
    lowered = url.lower()
    if lowered.endswith(".pdf"):
        return True
    if "sds" in lowered or "msds" in lowered or "safety-data-sheet" in lowered:
        return True
    return False


def _label_mentions_sds(label: str) -> bool:
    tokens = ("safety data sheet", "material safety data sheet", "sds", "msds")
    return any(token in label for token in tokens)
