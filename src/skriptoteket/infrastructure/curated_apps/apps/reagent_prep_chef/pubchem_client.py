from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Iterable, Protocol
from urllib.parse import quote

import httpx

_THROTTLE_STATUS_RE = re.compile(r"status:\s*(\w+)", re.IGNORECASE)


class AsyncClientProtocol(Protocol):
    async def get(self, url: str, *, params: dict | None = None) -> httpx.Response: ...

    async def aclose(self) -> None: ...


class PubChemClientProtocol(Protocol):
    @property
    def base_url(self) -> str: ...

    async def resolve_cids(
        self, *, queries: Iterable[str], max_candidates: int | None = None
    ) -> list[int]: ...

    async def fetch_lcss(self, *, cid: int) -> dict: ...

    async def fetch_heading(self, *, cid: int, heading: str) -> dict: ...

    async def fetch_linkout(self, *, cid: int) -> dict: ...

    async def fetch_properties_batch(
        self, *, cids: Iterable[int], properties: list[str]
    ) -> dict: ...

    async def autocomplete_compound(
        self, *, query: str, max_terms: int | None = None
    ) -> list[str]: ...


@dataclass(frozen=True, slots=True)
class PubChemClientSettings:
    base_url: str
    timeout_seconds: float
    user_agent: str
    listkey_max_wait_seconds: float
    listkey_poll_interval_seconds: float
    resolve_retry_attempts: int
    resolve_retry_backoff_seconds: float
    resolve_retry_backoff_max_seconds: float
    rate_limit_per_second: float
    max_in_flight: int
    throttle_yellow_delay_seconds: float
    throttle_red_delay_seconds: float


class _PubChemRateLimiter:
    def __init__(self, *, rate_limit_per_second: float, max_in_flight: int) -> None:
        safe_rate = rate_limit_per_second if rate_limit_per_second > 0 else 0.0
        self._min_interval = 1.0 / safe_rate if safe_rate > 0 else 0.0
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max(1, max_in_flight))
        self._next_allowed = 0.0
        self._throttle_until = 0.0

    async def acquire(self) -> None:
        await self._semaphore.acquire()
        async with self._lock:
            now = time.monotonic()
            wait_until = max(self._next_allowed, self._throttle_until)
            if wait_until > now:
                await asyncio.sleep(wait_until - now)
            now = time.monotonic()
            if self._min_interval > 0:
                self._next_allowed = max(self._next_allowed, now) + self._min_interval

    def release(self) -> None:
        self._semaphore.release()

    def apply_throttle(self, *, delay_seconds: float) -> None:
        if delay_seconds <= 0:
            return
        self._throttle_until = max(self._throttle_until, time.monotonic() + delay_seconds)


class PubChemClient:
    def __init__(self, *, settings: PubChemClientSettings) -> None:
        self._settings = settings
        self._client: AsyncClientProtocol = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            headers={"User-Agent": settings.user_agent},
        )
        self._rate_limiter = _PubChemRateLimiter(
            rate_limit_per_second=settings.rate_limit_per_second,
            max_in_flight=settings.max_in_flight,
        )

    @property
    def base_url(self) -> str:
        return self._settings.base_url

    async def close(self) -> None:
        await self._client.aclose()

    async def resolve_cid(self, *, queries: Iterable[str]) -> int | None:
        candidates = await self.resolve_cids(queries=queries, max_candidates=1)
        return candidates[0] if candidates else None

    async def resolve_cids(
        self, *, queries: Iterable[str], max_candidates: int | None = None
    ) -> list[int]:
        candidates: list[int] = []
        seen: set[int] = set()
        for query in queries:
            query = query.strip()
            if not query:
                continue
            cids = await self._resolve_cids_for_query(query)
            for cid in cids:
                if cid in seen:
                    continue
                seen.add(cid)
                candidates.append(cid)
                if max_candidates is not None and len(candidates) >= max_candidates:
                    return candidates
        return candidates

    async def fetch_pug_view(self, *, cid: int) -> dict:
        response = await self._get(f"/rest/pug_view/data/compound/{cid}/JSON")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem PUG-View payload was not a JSON object")
        return payload

    async def fetch_linkout(self, *, cid: int) -> dict:
        response = await self._get(f"/rest/pug_view/linkout/compound/{cid}/JSON")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem LinkOut payload was not a JSON object")
        return payload

    async def fetch_lcss(self, *, cid: int) -> dict:
        response = await self._get(
            f"/rest/pug_view/data/compound/{cid}/JSON",
            params={"toc": "LCSS TOC"},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem LCSS payload was not a JSON object")
        return payload

    async def fetch_heading(self, *, cid: int, heading: str) -> dict:
        response = await self._get(
            f"/rest/pug_view/data/compound/{cid}/JSON",
            params={"heading": heading},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem heading payload was not a JSON object")
        return payload

    async def fetch_synonyms(self, *, cid: int) -> list[str]:
        response = await self._get(f"/rest/pug/compound/cid/{cid}/synonyms/JSON")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem synonyms payload was not a JSON object")
        info_list = payload.get("InformationList")
        if not isinstance(info_list, dict):
            return []
        infos = info_list.get("Information")
        if not isinstance(infos, list):
            return []
        synonyms: list[str] = []
        for info in infos:
            if not isinstance(info, dict):
                continue
            values = info.get("Synonym")
            if isinstance(values, list):
                for entry in values:
                    if isinstance(entry, str):
                        synonyms.append(entry)
        return synonyms

    async def fetch_properties(self, *, cid: int, properties: list[str]) -> dict:
        prop_list = ",".join(properties)
        response = await self._get(f"/rest/pug/compound/cid/{cid}/property/{prop_list}/JSON")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem properties payload was not a JSON object")
        return payload

    async def fetch_properties_batch(self, *, cids: Iterable[int], properties: list[str]) -> dict:
        cid_values = [str(cid) for cid in cids if isinstance(cid, int)]
        if not cid_values:
            return {"PropertyTable": {"Properties": []}}
        prop_list = ",".join(properties)
        cid_list = ",".join(cid_values)
        response = await self._get(f"/rest/pug/compound/cid/{cid_list}/property/{prop_list}/JSON")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem properties payload was not a JSON object")
        return payload

    async def autocomplete_compound(self, *, query: str, max_terms: int | None = None) -> list[str]:
        encoded = quote(query, safe="")
        response = await self._get(f"/rest/autocomplete/compound/{encoded}/JSON")
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return []
        dictionary = payload.get("dictionary_terms")
        if not isinstance(dictionary, dict):
            return []
        terms = dictionary.get("compound")
        if not isinstance(terms, list):
            return []
        values = [term for term in terms if isinstance(term, str)]
        if max_terms is None:
            return values
        return values[:max_terms]

    async def _resolve_cids_for_query(self, query: str) -> list[int]:
        encoded = quote(query, safe="")
        endpoints = [f"/rest/pug/compound/name/{encoded}/cids/JSON"]
        if _looks_like_formula(query):
            endpoints.append(f"/rest/pug/compound/formula/{encoded}/cids/JSON")
        results: list[int] = []
        for endpoint in endpoints:
            response = await self._get_with_retry(endpoint)
            if response is None:
                continue
            if response.status_code == 404:
                continue
            if response.status_code == 202:
                payload = response.json()
                listkey = self._extract_listkey(payload)
                if listkey:
                    cids = await self._poll_listkey(listkey)
                    results.extend(cids)
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                continue
            results.extend(self._extract_cids(payload))
        return results

    def _extract_cids(self, payload: dict) -> list[int]:
        identifiers = payload.get("IdentifierList")
        if not isinstance(identifiers, dict):
            return []
        cids = identifiers.get("CID")
        if not isinstance(cids, list):
            return []
        return [cid for cid in cids if isinstance(cid, int)]

    def _extract_listkey(self, payload: dict) -> str | None:
        waiting = payload.get("Waiting")
        if not isinstance(waiting, dict):
            return None
        listkey = waiting.get("ListKey")
        return listkey if isinstance(listkey, str) and listkey else None

    async def _poll_listkey(self, listkey: str) -> list[int]:
        deadline = time.monotonic() + self._settings.listkey_max_wait_seconds
        while time.monotonic() <= deadline:
            response = await self._get(f"/rest/pug/compound/listkey/{listkey}/cids/JSON")
            if response.status_code == 202:
                await asyncio.sleep(self._settings.listkey_poll_interval_seconds)
                continue
            if response.status_code in {400, 404}:
                return []
            if response.status_code in {429, 503}:
                await asyncio.sleep(self._settings.listkey_poll_interval_seconds)
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                return []
            return self._extract_cids(payload)
        return []

    async def _get_with_retry(self, endpoint: str) -> httpx.Response | None:
        attempts = max(self._settings.resolve_retry_attempts, 1)
        backoff = self._settings.resolve_retry_backoff_seconds
        max_backoff = self._settings.resolve_retry_backoff_max_seconds
        for attempt in range(1, attempts + 1):
            try:
                response = await self._get(endpoint)
            except httpx.RequestError:
                if attempt == attempts:
                    return None
                await asyncio.sleep(min(max_backoff, backoff * (2 ** (attempt - 1))))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == attempts:
                    return None
                await asyncio.sleep(min(max_backoff, backoff * (2 ** (attempt - 1))))
                continue
            return response
        return None

    async def _get(self, url: str, *, params: dict | None = None) -> httpx.Response:
        await self._rate_limiter.acquire()
        try:
            response = await self._client.get(url, params=params)
        finally:
            self._rate_limiter.release()
        self._apply_throttle_from_response(response)
        return response

    def _apply_throttle_from_response(self, response: httpx.Response) -> None:
        delay = 0.0
        header = response.headers.get("X-Throttling-Control")
        if isinstance(header, str):
            delay = max(delay, self._delay_from_throttling_control(header))
        retry_after = response.headers.get("Retry-After")
        delay = max(delay, _parse_retry_after_seconds(retry_after))
        if response.status_code == 429 or response.status_code >= 500:
            delay = max(delay, self._settings.throttle_red_delay_seconds)
        if delay > 0:
            self._rate_limiter.apply_throttle(delay_seconds=delay)

    def _delay_from_throttling_control(self, header: str) -> float:
        statuses = [value.lower() for value in _THROTTLE_STATUS_RE.findall(header)]
        if any(status in {"red", "black"} for status in statuses):
            return self._settings.throttle_red_delay_seconds
        if any(status in {"yellow", "orange"} for status in statuses):
            return self._settings.throttle_yellow_delay_seconds
        return 0.0


def _parse_retry_after_seconds(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        seconds = float(value.strip())
    except ValueError:
        return 0.0
    return seconds if seconds > 0 else 0.0


def _looks_like_formula(value: str) -> bool:
    if not value:
        return False
    if not re.fullmatch(r"[A-Za-z0-9().·]+", value):
        return False
    return bool(re.search(r"[A-Z]", value))
