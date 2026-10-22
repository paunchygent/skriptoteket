"""httpx client for HuleEdu's LLM provider door.

Purpose:
    Send exam OpenAI request bodies unchanged to the door's internal routes
    (ST-HULE-14-03 D1-D5) with Skriptoteket's internal key, service id, the
    teacher's user id, the exempt flag and the paid-overage mode, admit the
    caller's AI action on its first successful call, count its paid overage from
    the door's charge headers and stop it once a charge passes the per-job cap
    (C7), and turn a limit 429 into ``AiDailyLimitReached`` with its
    ``error.limit``. A streamed call (``stream``) relays the upstream SSE lines
    under the same slots and capacity retries as ``send``, holds its slots
    until the stream closes, and admits the caller on a 2xx; the door sends no
    charge headers on a stream, so a stream records no overage charge.

Relationships:
    Implements ``protocols.llm_door.LlmDoorClientProtocol``; composed in
    ``di.llm_door``. This is the only module allowed to reach the door.
"""

from __future__ import annotations

import asyncio
import json
import weakref
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from dataclasses import dataclass

import httpx
import structlog
from pydantic import JsonValue

from skriptoteket.config import Settings
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
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
from skriptoteket.protocols.sleeper import SleeperProtocol

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


@dataclass(frozen=True, slots=True)
class DoorBounds:
    """How much one process asks of the door, and how it waits when refused.

    Built from ``Settings`` (``LLM_DOOR_*``, ``LLM_JOB_MAX_IN_FLIGHT``) by
    ``from_settings``.
    """

    max_in_flight: int
    slot_wait_seconds: float
    per_action_max_in_flight: int
    pool_timeout_seconds: float
    capacity_retries: int
    retry_after_max_seconds: float
    retry_after_fallback_seconds: float

    @classmethod
    def from_settings(cls, settings: Settings) -> DoorBounds:
        return cls(
            max_in_flight=settings.LLM_DOOR_MAX_IN_FLIGHT,
            slot_wait_seconds=settings.LLM_DOOR_SLOT_WAIT_SECONDS,
            per_action_max_in_flight=settings.LLM_JOB_MAX_IN_FLIGHT,
            pool_timeout_seconds=settings.LLM_DOOR_POOL_TIMEOUT_SECONDS,
            capacity_retries=settings.LLM_DOOR_CAPACITY_RETRIES,
            retry_after_max_seconds=settings.LLM_DOOR_RETRY_AFTER_MAX_SECONDS,
            retry_after_fallback_seconds=settings.LLM_DOOR_RETRY_AFTER_FALLBACK_SECONDS,
        )

    def __post_init__(self) -> None:
        if self.max_in_flight < 1 or self.per_action_max_in_flight < 1:
            raise ValueError("Door in-flight bounds must be at least 1.")
        if self.capacity_retries < 0:
            raise ValueError("The door capacity retry count cannot be negative.")
        if (
            self.slot_wait_seconds <= 0
            or self.pool_timeout_seconds <= 0
            or self.retry_after_max_seconds <= 0
            or self.retry_after_fallback_seconds <= 0
        ):
            raise ValueError("Door wait times must be positive.")


class HuleEduLlmDoorClient(LlmDoorClientProtocol):
    """Door client over one shared ``httpx.AsyncClient`` with bounded fan-out."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str,
        internal_api_key: str,
        job_overage_cap_usd_micros: int,
        sleeper: SleeperProtocol,
        bounds: DoorBounds,
    ) -> None:
        if not base_url.strip():
            raise ValueError("LLM provider door base_url must be non-empty.")
        if job_overage_cap_usd_micros < 0:
            raise ValueError("The per-job overage cap cannot be negative.")
        self._client = client
        self._base_url = base_url.strip().rstrip("/")
        self._internal_api_key = internal_api_key.strip()
        self._cap_usd_micros = job_overage_cap_usd_micros
        self._sleeper = sleeper
        self._bounds = bounds
        self._process_slots = asyncio.Semaphore(self._bounds.max_in_flight)
        self._action_slots: weakref.WeakKeyDictionary[AiDoorCaller, asyncio.Semaphore] = (
            weakref.WeakKeyDictionary()
        )

    async def send(
        self,
        *,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> DoorReply:
        for resends in range(self._bounds.capacity_retries + 1):
            async with self._slots(caller):
                # Checked once the slot is held: calls queued behind it must see
                # the charges settled while they waited, not the queue-time total.
                caller.require_within_overage_cap(cap_usd_micros=self._cap_usd_micros)
                response = await self._post(operation, payload, caller, timeout_seconds)
            if response.status_code != 429:
                break
            limit = _limit_of(response.content)
            if limit is not None:
                raise AiDailyLimitReached(limit=limit)
            retry_after = _retry_after_seconds(response)
            if resends == self._bounds.capacity_retries:
                raise AiDoorBusy(retry_after_seconds=retry_after)
            await self._sleeper.sleep(self._capacity_wait_seconds(retry_after))
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
        """Open one streamed call that holds its door slots until the stream closes."""

        for resends in range(self._bounds.capacity_retries + 1):
            async with AsyncExitStack() as held:
                await held.enter_async_context(self._slots(caller))
                caller.require_within_overage_cap(cap_usd_micros=self._cap_usd_micros)
                body = b""
                with _door_transport_errors():
                    response = await held.enter_async_context(
                        self._client.stream(
                            "POST",
                            f"{self._base_url}{_DOOR_PATH}/{operation.value}",
                            headers=_caller_headers(self._internal_api_key, caller),
                            json=dict(payload),
                            timeout=httpx.Timeout(
                                timeout_seconds, pool=self._bounds.pool_timeout_seconds
                            ),
                        )
                    )
                    if response.status_code >= 400:
                        body = await response.aread()
                if response.status_code != 429:
                    door_stream = _HttpxDoorStream(response=response, body=body)
                    if door_stream.is_success:
                        caller.admit()
                    yield door_stream
                    return
            limit = _limit_of(body)
            if limit is not None:
                raise AiDailyLimitReached(limit=limit)
            retry_after = _retry_after_seconds(response)
            if resends == self._bounds.capacity_retries:
                raise AiDoorBusy(retry_after_seconds=retry_after)
            await self._sleeper.sleep(self._capacity_wait_seconds(retry_after))

    @asynccontextmanager
    async def _slots(self, caller: AiDoorCaller) -> AsyncIterator[None]:
        """Hold one of the action's slots, then one of the process's.

        An action waits for its own slots without limit (a job legitimately
        queues behind itself); a wait for a process slot ends as ``AiDoorBusy``.
        """

        async with self._action_semaphore(caller):
            try:
                async with asyncio.timeout(self._bounds.slot_wait_seconds):
                    await self._process_slots.acquire()
            except TimeoutError as exc:
                raise AiDoorBusy(retry_after_seconds=None) from exc
            try:
                yield
            finally:
                self._process_slots.release()

    def _action_semaphore(self, caller: AiDoorCaller) -> asyncio.Semaphore:
        semaphore = self._action_slots.get(caller)
        if semaphore is None:
            semaphore = asyncio.Semaphore(self._bounds.per_action_max_in_flight)
            self._action_slots[caller] = semaphore
        return semaphore

    def _capacity_wait_seconds(self, retry_after: int | None) -> float:
        wait = (
            self._bounds.retry_after_fallback_seconds if retry_after is None else float(retry_after)
        )
        return min(wait, self._bounds.retry_after_max_seconds)

    async def _post(
        self,
        operation: DoorOperation,
        payload: Mapping[str, JsonValue],
        caller: AiDoorCaller,
        timeout_seconds: float,
    ) -> httpx.Response:
        with _door_transport_errors():
            return await self._client.post(
                f"{self._base_url}{_DOOR_PATH}/{operation.value}",
                headers=_caller_headers(self._internal_api_key, caller),
                json=dict(payload),
                timeout=httpx.Timeout(timeout_seconds, pool=self._bounds.pool_timeout_seconds),
            )


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
    """Map httpx transport failures; a wait for a pooled connection is a busy door."""

    try:
        yield
    except httpx.PoolTimeout as exc:
        raise AiDoorBusy(retry_after_seconds=None) from exc
    except httpx.TimeoutException as exc:
        raise DoorTimeout("LLM provider door call timed out.") from exc
    except httpx.RequestError as exc:
        raise DoorRequestFailed("LLM provider door call failed before an answer.") from exc


def _retry_after_seconds(response: httpx.Response) -> int | None:
    """The door's ``Retry-After`` in whole seconds, or None when absent or not a number."""

    raw = response.headers.get("Retry-After", "").strip()
    if raw.isascii() and raw.isdigit():
        return int(raw)
    return None


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
    (``openai_door_admission_full``) names none and is retried by ``send``.
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
