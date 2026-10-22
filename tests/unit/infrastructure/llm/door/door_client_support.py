"""Door client construction and canned responses shared by the door client tests."""

from __future__ import annotations

from uuid import UUID

import httpx
from pydantic import JsonValue

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.door.client import DoorBounds, HuleEduLlmDoorClient

TEACHER = UUID("11111111-1111-1111-1111-111111111111")
PAYLOAD: dict[str, JsonValue] = {"model": "gpt-6-luna", "input": "hej", "max_output_tokens": 64}


class InstantSleeper:
    async def sleep(self, seconds: float) -> None:
        del seconds


def make_door_client(handler: httpx.MockTransport) -> HuleEduLlmDoorClient:
    return HuleEduLlmDoorClient(
        sleeper=InstantSleeper(),
        client=httpx.AsyncClient(transport=handler),
        base_url="http://door.test:8080/",
        internal_api_key="internal-key",
        job_overage_cap_usd_micros=1_000_000,
        bounds=DoorBounds.from_settings(Settings()),
    )


def refusal_response(code: str, limit: str | None = None) -> httpx.Response:
    return httpx.Response(
        429,
        headers={"Retry-After": "3600"},
        json={
            "error": {
                "type": "huleedu_openai_door",
                "code": code,
                "message": "refused",
                "limit": limit,
            }
        },
    )
