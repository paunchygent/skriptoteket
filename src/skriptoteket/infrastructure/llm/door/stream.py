"""Consume private door settlement events without exposing billing as provider text."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator, Callable, Mapping

from skriptoteket.protocols.llm_door import DoorStream

_CHARGE_EVENT = "huleedu.door.charge"


class ChargeRecordingDoorStream(DoorStream):
    """Relay provider SSE events and settle one charge, including on early consumer exit.

    Events are buffered only until their SSE boundary. The context owner must call
    ``finish`` before closing the transport when a provider consumer stops at
    its own terminal event. Exceptional exits close without draining. Missing or
    malformed charge metadata uses the existing
    missing-charge policy through ``record_charge({})``.
    """

    def __init__(
        self,
        *,
        stream: DoorStream,
        record_charge: Callable[[Mapping[str, str]], None],
    ) -> None:
        self._stream = stream
        self._record_charge = record_charge
        self._recorded = False
        self._finished = False
        self._lines = self._provider_lines()

    @property
    def status_code(self) -> int:
        return self._stream.status_code

    @property
    def headers(self) -> Mapping[str, str]:
        return self._stream.headers

    @property
    def body(self) -> bytes:
        return self._stream.body

    @property
    def is_success(self) -> bool:
        return self._stream.is_success

    async def aiter_lines(self) -> AsyncIterator[str]:
        async for line in self._lines:
            yield line

    async def finish(self, *, drain: bool = True) -> None:
        if self._finished:
            return
        try:
            if drain:
                async for _ in self._lines:
                    pass
            else:
                await self._lines.aclose()
        finally:
            self._finished = True
            if not self._recorded:
                self._recorded = True
                self._record_charge({})

    async def _provider_lines(self) -> AsyncGenerator[str, None]:
        event_lines: list[str] = []
        async for line in self._stream.aiter_lines():
            if line:
                event_lines.append(line)
                continue
            if not self._consume_charge(event_lines):
                for provider_line in event_lines:
                    yield provider_line
                yield ""
            event_lines = []
        # An unfinished event cannot constitute a settled control record. Preserve
        # provider bytes, but never leak a partial private event into model text.
        if event_lines and not self._is_charge(event_lines):
            for provider_line in event_lines:
                yield provider_line

    @staticmethod
    def _is_charge(lines: list[str]) -> bool:
        return any(
            line.startswith("event:") and line[6:].strip() == _CHARGE_EVENT for line in lines
        )

    def _consume_charge(self, lines: list[str]) -> bool:
        if not self._is_charge(lines):
            return False
        if self._recorded:
            return True
        data = "\n".join(line[5:].lstrip(" ") for line in lines if line.startswith("data:"))
        try:
            charge: object = json.loads(data)
        except ValueError:
            return True
        if not isinstance(charge, dict):
            return True
        kind = charge.get("charge_kind")
        micros = charge.get("charge_usd_micros")
        if (
            charge.get("type") != _CHARGE_EVENT
            or kind not in ("complimentary", "overage")
            or not isinstance(micros, int)
            or isinstance(micros, bool)
            or micros < 0
        ):
            return True
        self._recorded = True
        self._record_charge(
            {"X-HuleEdu-Charge-Kind": kind, "X-HuleEdu-Charge-USD-Micros": str(micros)}
        )
        return True
