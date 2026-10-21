"""httpx client for HuleEdu's LLM provider door.

Purpose:
    Send exam OpenAI request bodies unchanged to the door's internal routes
    (ST-HULE-14-03 D1-D5) with Skriptoteket's internal key, service id, the
    teacher's user id, the exempt flag and the paid-overage mode, and turn a
    limit 429 into ``AiDailyLimitReached``.

Relationships:
    Implements ``protocols.llm_door.LlmDoorClientProtocol``; composed in
    ``di.llm_door``. This is the only module allowed to reach the door.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

import httpx
from pydantic import JsonValue

from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, AiDoorCaller
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorReply,
    DoorRequestFailed,
    DoorTimeout,
    LlmDoorClientProtocol,
)

SERVICE_ID = "skriptoteket"
_DOOR_PATH = "/internal/v1/openai"
_FREE_ALLOWANCE_ONLY = "free_allowance_only"
_ALLOW_PAID_OVERAGE = "allow_paid_overage"
_LIMIT_BY_CODE: dict[str, AiDailyLimit] = {
    "openai_complimentary_allowance_exceeded": AiDailyLimit.POOL,
    "openai_caller_user_share_exceeded": AiDailyLimit.USER_SHARE,
    "openai_caller_usd_ceiling_exceeded": AiDailyLimit.USD_CEILING,
}


class HuleEduLlmDoorClient(LlmDoorClientProtocol):
    """Door client over one shared ``httpx.AsyncClient``."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str,
        internal_api_key: str,
    ) -> None:
        if not base_url.strip():
            raise ValueError("LLM provider door base_url must be non-empty.")
        self._client = client
        self._base_url = base_url.strip().rstrip("/")
        self._internal_api_key = internal_api_key.strip()

    async def send(
        self,
        *,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> DoorReply:
        try:
            response = await self._client.post(
                f"{self._base_url}{_DOOR_PATH}/{operation.value}",
                headers=_caller_headers(self._internal_api_key, caller),
                json=dict(payload),
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise DoorTimeout("LLM provider door call timed out.") from exc
        except httpx.RequestError as exc:
            raise DoorRequestFailed("LLM provider door call failed before an answer.") from exc
        if response.status_code == 429:
            limit = _limit_of(response.content)
            if limit is not None:
                raise AiDailyLimitReached(limit=limit)
        return DoorReply(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
        )


def _caller_headers(internal_api_key: str, caller: AiDoorCaller) -> dict[str, str]:
    headers = {
        "X-Internal-API-Key": internal_api_key,
        "X-Service-ID": SERVICE_ID,
        "X-HuleEdu-User-ID": str(caller.user_id),
        "X-HuleEdu-OpenAI-Allowance-Mode": (
            _ALLOW_PAID_OVERAGE if caller.allow_paid_overage else _FREE_ALLOWANCE_ONLY
        ),
    }
    if caller.exempt:
        headers["X-HuleEdu-Exempt-Test-User"] = "true"
    return headers


def _limit_of(body: bytes) -> AiDailyLimit | None:
    """Read the limit a door 429 names; a capacity 429 names none."""

    try:
        decoded: object = json.loads(body)
    except ValueError:
        return None
    if not isinstance(decoded, dict):
        return None
    error = decoded.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return _LIMIT_BY_CODE.get(code) if isinstance(code, str) else None
