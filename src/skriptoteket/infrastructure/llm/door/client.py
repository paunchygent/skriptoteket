"""httpx client for HuleEdu's LLM provider door.

Purpose:
    Send exam OpenAI request bodies unchanged to the door's internal routes
    (ST-HULE-14-03 D1-D5) with Skriptoteket's internal key, service id, the
    teacher's user id, the exempt flag and the paid-overage mode, admit the
    caller's AI action on its first successful call, count its paid overage from
    the door's charge headers and stop it once a charge passes the per-job cap
    (C7), and turn a limit 429 into ``AiDailyLimitReached`` with its
    ``error.limit``. A streamed call (``stream``) relays the upstream SSE lines
    and admits the caller on a 2xx; the door sends no charge headers on a
    stream, so a stream records no overage charge.

Relationships:
    Implements ``protocols.llm_door.LlmDoorClientProtocol``; composed in
    ``di.llm_door``. This is the only module allowed to reach the door.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager

import httpx
import structlog
from pydantic import JsonValue

from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
)
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorReply,
    DoorRequestFailed,
    DoorStream,
    DoorTimeout,
    LlmDoorClientProtocol,
)

logger = structlog.get_logger(__name__)

SERVICE_ID = "skriptoteket"
_CHARGE_KIND_HEADER = "X-HuleEdu-Charge-Kind"
_CHARGE_MICROS_HEADER = "X-HuleEdu-Charge-USD-Micros"
_OVERAGE = "overage"
_DOOR_PATH = "/internal/v1/openai"
_FREE_ALLOWANCE_ONLY = "free_allowance_only"
_ALLOW_PAID_OVERAGE = "allow_paid_overage"
_LIMIT_CODES = frozenset(
    {
        "openai_complimentary_allowance_exceeded",
        "openai_caller_user_share_exceeded",
        "openai_caller_usd_ceiling_exceeded",
    }
)


class HuleEduLlmDoorClient(LlmDoorClientProtocol):
    """Door client over one shared ``httpx.AsyncClient``."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str,
        internal_api_key: str,
        job_overage_cap_usd_micros: int,
    ) -> None:
        if not base_url.strip():
            raise ValueError("LLM provider door base_url must be non-empty.")
        if job_overage_cap_usd_micros < 0:
            raise ValueError("The per-job overage cap cannot be negative.")
        self._client = client
        self._base_url = base_url.strip().rstrip("/")
        self._internal_api_key = internal_api_key.strip()
        self._cap_usd_micros = job_overage_cap_usd_micros

    async def send(
        self,
        *,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> DoorReply:
        caller.require_within_overage_cap(cap_usd_micros=self._cap_usd_micros)
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
        reply = DoorReply(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
        )
        settle_door_reply(caller, reply, cap_usd_micros=self._cap_usd_micros)
        return reply

    @asynccontextmanager
    async def stream(
        self,
        *,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> AsyncIterator[DoorStream]:
        caller.require_within_overage_cap(cap_usd_micros=self._cap_usd_micros)
        async with AsyncExitStack() as connection:
            body = b""
            with _door_transport_errors():
                response = await connection.enter_async_context(
                    self._client.stream(
                        "POST",
                        f"{self._base_url}{_DOOR_PATH}/{operation.value}",
                        headers=_caller_headers(self._internal_api_key, caller),
                        json=dict(payload),
                        timeout=timeout_seconds,
                    )
                )
                if response.status_code >= 400:
                    body = await response.aread()
            if response.status_code == 429:
                limit = _limit_of(body)
                if limit is not None:
                    raise AiDailyLimitReached(limit=limit)
            door_stream = _HttpxDoorStream(response=response, body=body)
            if door_stream.is_success:
                caller.admit()
            yield door_stream


class _HttpxDoorStream(DoorStream):
    """One open httpx streamed answer; a failed answer carries its body and no lines."""

    def __init__(self, *, response: httpx.Response, body: bytes) -> None:
        self._response = response
        self._body = body

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> Mapping[str, str]:
        return self._response.headers

    @property
    def body(self) -> bytes:
        return self._body

    @property
    def is_success(self) -> bool:
        return 200 <= self._response.status_code < 300

    async def aiter_lines(self) -> AsyncIterator[str]:
        if not self.is_success:
            return
        with _door_transport_errors():
            async for line in self._response.aiter_lines():
                yield line


@contextmanager
def _door_transport_errors() -> Iterator[None]:
    try:
        yield
    except httpx.TimeoutException as exc:
        raise DoorTimeout("LLM provider door call timed out.") from exc
    except httpx.RequestError as exc:
        raise DoorRequestFailed("LLM provider door call failed before an answer.") from exc


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
    """Read the limit a door limit 429 names in ``error.limit``.

    Only the three limit refusal codes carry a limit; a capacity 429
    (``openai_door_admission_full``) names none and returns as a reply.
    """

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
    limit = error.get("limit")
    if code not in _LIMIT_CODES or not isinstance(limit, str):
        return None
    try:
        return AiDailyLimit(limit)
    except ValueError:
        return None


def settle_door_reply(caller: AiDoorCaller, reply: DoorReply, *, cap_usd_micros: int) -> None:
    """Settle one door answer on its AI action.

    A success admits the action; the call's overage charge is added; a charge
    that takes an app job past the cap stops it now, so the call that crosses
    the cap never returns as an ordinary success (C7).
    """

    if reply.is_success:
        caller.admit()
    record_door_charge(caller, reply.headers)
    caller.require_within_overage_cap(cap_usd_micros=cap_usd_micros)


def record_door_charge(caller: AiDoorCaller, headers: Mapping[str, str]) -> None:
    """Add the door's overage charge for one call to the caller's action.

    A call without charge headers counts no overage. The door sends none for
    exempt callers, so only a non-exempt caller's missing headers are logged.
    """

    charge = httpx.Headers(headers)
    kind = charge.get(_CHARGE_KIND_HEADER)
    raw_micros = charge.get(_CHARGE_MICROS_HEADER)
    if kind is None or raw_micros is None:
        if not caller.exempt:
            logger.warning("llm_door_charge_headers_missing", user_id=str(caller.user_id))
        return
    if kind != _OVERAGE:
        return
    try:
        micros = int(raw_micros)
    except ValueError:
        logger.warning("llm_door_charge_header_invalid", value=raw_micros)
        return
    if micros > 0:
        caller.charge_overage(micros)
