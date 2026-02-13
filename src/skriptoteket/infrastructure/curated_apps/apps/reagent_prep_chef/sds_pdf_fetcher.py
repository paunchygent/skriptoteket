from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass

import httpx
import structlog

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.pubchem_client import (
    AsyncClientProtocol,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_fetcher_settings import (
    ProgressReporter,
    SdsFetcherSettings,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_pdf_text,
    is_sds_document,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_providers import (
    SdsPdfCandidate,
    SdsPdfProviderContext,
    SdsPdfProviderRegistry,
)


@dataclass(frozen=True, slots=True)
class SdsPdfDocument:
    sds_bytes: bytes
    text: str
    media_type: str
    source_url: str


class SdsPdfFetcher:
    """Fetch and validate PDF SDS documents from registered providers."""

    def __init__(
        self,
        *,
        settings: SdsFetcherSettings,
        progress: ProgressReporter | None = None,
        http_client: AsyncClientProtocol | None = None,
        provider_registry: SdsPdfProviderRegistry | None = None,
    ) -> None:
        self._settings = settings
        self._progress = progress
        self._http_client = http_client
        self._provider_registry = provider_registry or SdsPdfProviderRegistry.default(
            progress=progress
        )

    async def fetch(
        self,
        *,
        context: SdsPdfProviderContext,
        log: structlog.stdlib.BoundLogger,
    ) -> SdsPdfDocument | None:
        candidates = await self._provider_registry.collect_candidates(
            context=context,
            log=log,
        )
        if not candidates:
            self._emit(log, "sds_pdf_candidates_missing")
            return None

        ordered = sorted(candidates, key=score_sds_candidate, reverse=True)
        self._emit(log, "sds_pdf_candidates", count=len(ordered))

        for index, candidate in enumerate(ordered, start=1):
            self._emit(
                log,
                "sds_pdf_candidate",
                index=index,
                total=len(ordered),
                url=candidate.url,
                source=candidate.source,
            )
            document = await self._download_pdf(url=candidate.url, log=log)
            if document is None:
                continue
            return document
        return None

    async def _download_pdf(
        self, *, url: str, log: structlog.stdlib.BoundLogger
    ) -> SdsPdfDocument | None:
        attempts = max(self._settings.retry_attempts, 1)
        for attempt in range(1, attempts + 1):
            self._emit(log, "sds_pdf_fetch_start", url=url, attempt=attempt, attempts=attempts)
            start = time.monotonic()
            try:
                response = await self._get_url(url)
            except httpx.HTTPError as exc:
                elapsed = time.monotonic() - start
                self._emit(
                    log,
                    "sds_pdf_fetch_error",
                    url=url,
                    attempt=attempt,
                    elapsed_seconds=round(elapsed, 2),
                    error=str(exc),
                )
                if attempt == attempts:
                    return None
                await self._backoff_sleep(attempt=attempt)
                continue
            elapsed = time.monotonic() - start
            status = response.status_code
            self._emit(
                log,
                "sds_pdf_fetch_done",
                url=url,
                attempt=attempt,
                elapsed_seconds=round(elapsed, 2),
                status_code=status,
            )
            if status >= 400:
                if attempt == attempts:
                    return None
                await self._backoff_sleep(attempt=attempt)
                continue

            body = response.content
            if not looks_like_pdf(body=body):
                self._emit(
                    log,
                    "sds_pdf_not_pdf",
                    url=url,
                )
                return None

            text = extract_pdf_text(body)
            if not is_sds_document(text):
                self._emit(log, "sds_pdf_not_sds", url=url)
                return None

            return SdsPdfDocument(
                sds_bytes=body,
                text=text,
                media_type="application/pdf",
                source_url=str(response.url),
            )
        return None

    async def _get_url(self, url: str) -> httpx.Response:
        if self._http_client is not None:
            return await self._http_client.get(url)
        async with httpx.AsyncClient(
            timeout=self._settings.timeout_seconds,
            headers={"User-Agent": self._settings.user_agent},
            follow_redirects=True,
        ) as client:
            return await client.get(url)

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


def score_sds_candidate(candidate: SdsPdfCandidate) -> int:
    """Score candidates; higher means preferred."""
    score = candidate.score_bias
    url = candidate.url.lower()
    label = (candidate.label or "").lower()
    if url.endswith(".pdf"):
        score += 5
    if "sds" in url or "msds" in url or "safety-data-sheet" in url:
        score += 8
    if "safety data sheet" in label or "sds" in label or "msds" in label:
        score += 10
    return score


def looks_like_pdf(*, body: bytes) -> bool:
    """Return True if the payload looks like a PDF file."""
    return body.startswith(b"%PDF")
