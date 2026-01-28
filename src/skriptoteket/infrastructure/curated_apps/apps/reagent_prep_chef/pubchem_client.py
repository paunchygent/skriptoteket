from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from urllib.parse import quote

import httpx


@dataclass(frozen=True, slots=True)
class PubChemClientSettings:
    base_url: str
    timeout_seconds: float
    user_agent: str


class PubChemClient:
    def __init__(self, *, settings: PubChemClientSettings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
            headers={"User-Agent": settings.user_agent},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def resolve_cid(self, *, queries: Iterable[str]) -> int | None:
        for query in queries:
            query = query.strip()
            if not query:
                continue
            cid = await self._resolve_cid_for_query(query)
            if cid is not None:
                return cid
        return None

    async def fetch_pug_view(self, *, cid: int) -> dict:
        response = await self._client.get(f"/rest/pug_view/data/compound/{cid}/JSON")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem PUG-View payload was not a JSON object")
        return payload

    async def fetch_linkout(self, *, cid: int) -> dict:
        response = await self._client.get(f"/rest/pug_view/linkout/compound/{cid}/JSON")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("PubChem LinkOut payload was not a JSON object")
        return payload

    async def _resolve_cid_for_query(self, query: str) -> int | None:
        encoded = quote(query, safe="")
        endpoints = [
            f"/rest/pug/compound/name/{encoded}/cids/JSON",
            f"/rest/pug/compound/formula/{encoded}/cids/JSON",
        ]
        for endpoint in endpoints:
            response = await self._client.get(endpoint)
            if response.status_code == 404:
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                continue
            identifiers = payload.get("IdentifierList")
            if not isinstance(identifiers, dict):
                continue
            cids = identifiers.get("CID")
            if isinstance(cids, list) and cids:
                cid = cids[0]
                if isinstance(cid, int):
                    return cid
        return None
