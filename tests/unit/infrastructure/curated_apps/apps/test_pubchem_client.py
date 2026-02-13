from __future__ import annotations

import httpx
import pytest

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.pubchem_client import (
    PubChemClient,
    PubChemClientSettings,
)


class FakeAsyncClient:
    def __init__(self, responses: dict[str, list[httpx.Response]]) -> None:
        self._responses = responses

    async def get(self, url: str, params: dict | None = None) -> httpx.Response:
        key = url
        if params:
            key = f"{url}?{_serialize_params(params)}"
        responses = self._responses.get(key)
        if not responses:
            raise AssertionError(f"Unexpected request: {key}")
        return responses.pop(0)

    async def aclose(self) -> None:
        return None


def _serialize_params(params: dict) -> str:
    pairs = [f"{key}={value}" for key, value in params.items()]
    return "&".join(pairs)


def _response(status_code: int, payload: dict) -> httpx.Response:
    request = httpx.Request("GET", "https://pubchem.test")
    return httpx.Response(status_code, json=payload, request=request)


@pytest.mark.asyncio
async def test_resolve_cids_polls_listkey() -> None:
    settings = PubChemClientSettings(
        base_url="https://pubchem.test",
        timeout_seconds=1.0,
        user_agent="test",
        listkey_max_wait_seconds=1.0,
        listkey_poll_interval_seconds=0.0,
        resolve_retry_attempts=1,
        resolve_retry_backoff_seconds=0.0,
        resolve_retry_backoff_max_seconds=0.0,
        rate_limit_per_second=0.0,
        max_in_flight=1,
        throttle_yellow_delay_seconds=0.0,
        throttle_red_delay_seconds=0.0,
    )
    client = PubChemClient(settings=settings)
    listkey = "abc123"
    client._client = FakeAsyncClient(
        {
            "/rest/pug/compound/name/NH4NO3/cids/JSON": [
                _response(202, {"Waiting": {"ListKey": listkey}})
            ],
            f"/rest/pug/compound/listkey/{listkey}/cids/JSON": [
                _response(202, {"Waiting": {"ListKey": listkey}}),
                _response(200, {"IdentifierList": {"CID": [22985]}}),
            ],
            "/rest/pug/compound/formula/NH4NO3/cids/JSON": [_response(404, {})],
        }
    )

    cids = await client.resolve_cids(queries=["NH4NO3"])

    assert cids == [22985]
