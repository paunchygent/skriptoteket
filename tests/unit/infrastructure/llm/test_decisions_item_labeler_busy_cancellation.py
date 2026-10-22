"""A busy Decisions chunk ends the action: sibling chunk requests are cancelled and joined.

Gated fake door calls stand in for in-flight provider requests. A sibling that is
released would return a success, so every test asserts the gate stayed shut.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, AiDoorBusy
from skriptoteket.protocols.item_type_labeler import (
    ContentTagClassificationRequest,
    LabelingItem,
    LabelingRequest,
)
from skriptoteket.protocols.llm_door import DoorReply
from tests.unit.infrastructure.llm.decisions_item_labeler_support import Harness, sent_payload
from tests.unit.llm_door_fakes import DoorSent, fixture_caller

pytestmark = pytest.mark.unit

# 401 items split into chunks of 200, 200 and 1 question.
_ITEMS = tuple(LabelingItem(f"item-{number}", "Fråga") for number in range(401))
_CONTENT = (ExamContentItem(id="GY:SVESVE02:grammatik", text="Svenska språkets uppbyggnad."),)
_CHUNK_SIZES = (200, 200, 1)
_PROMPT_SECONDS = 2.0

Action = Callable[[Harness], Awaitable[object]]


async def _label(harness: Harness) -> object:
    request = LabelingRequest(job_id=uuid4(), items=_ITEMS, caller=fixture_caller())
    return await harness.labeler().label(request=request)


async def _classify(harness: Harness) -> object:
    request = ContentTagClassificationRequest(
        job_id=uuid4(), items=_ITEMS, content_items=_CONTENT, caller=fixture_caller()
    )
    return await harness.labeler().classify_content(request=request)


_ACTIONS = pytest.mark.parametrize("action", [_label, _classify], ids=["label", "classify"])


class ChunkGates:
    """Door calls keyed by chunk size, each answered by its own script."""

    def __init__(self) -> None:
        self.started: list[int] = []
        self.cancelled: list[int] = []
        self.released: list[int] = []
        self.all_started = asyncio.Event()
        self.release = asyncio.Event()

    def _start(self, sent: DoorSent) -> int:
        size = len(sent_payload(sent)["questions"])
        self.started.append(size)
        if len(self.started) == len(_CHUNK_SIZES):
            self.all_started.set()
        return size

    async def _hold(self, size: int) -> None:
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled.append(size)
            raise
        self.released.append(size)

    async def respond_busy_on_last_chunk(self, sent: DoorSent) -> DoorReply:
        size = self._start(sent)
        if size == _CHUNK_SIZES[-1]:
            await self.all_started.wait()
            raise AiDoorBusy(retry_after_seconds=7)
        await self._hold(size)
        raise AssertionError("a gated sibling must be cancelled, not released")

    async def respond_all_gated(self, sent: DoorSent) -> DoorReply:
        await self._hold(self._start(sent))
        raise AssertionError("a gated chunk must be cancelled, not released")

    async def respond_limits(self, sent: DoorSent) -> DoorReply:
        """Chunk 1 refuses USER_SHARE late, chunk 2 refuses POOL at once, chunk 3 refuses late."""

        size = self._start(sent)
        order = len(self.started)
        if order == 2:
            await self.all_started.wait()
            self.release.set()
            raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
        await self._hold(size)
        raise AiDailyLimitReached(
            limit=AiDailyLimit.USER_SHARE if order == 1 else AiDailyLimit.USD_CEILING
        )


@_ACTIONS
async def test_busy_chunk_cancels_and_joins_sibling_chunks(action: Action) -> None:
    gates = ChunkGates()
    harness = Harness(gates.respond_busy_on_last_chunk)

    with pytest.raises(AiDoorBusy) as caught:
        async with asyncio.timeout(_PROMPT_SECONDS):
            await action(harness)

    assert caught.value.retry_after_seconds == 7
    assert sorted(gates.cancelled) == [200, 200]
    assert gates.released == []


@_ACTIONS
async def test_parent_cancellation_cancels_and_joins_every_chunk(action: Action) -> None:
    gates = ChunkGates()
    harness = Harness(gates.respond_all_gated)
    running = asyncio.ensure_future(action(harness))
    async with asyncio.timeout(_PROMPT_SECONDS):
        await gates.all_started.wait()

    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running

    assert sorted(gates.cancelled) == sorted(_CHUNK_SIZES)
    assert gates.released == []


@_ACTIONS
async def test_daily_limit_waits_for_every_chunk_and_raises_first_in_call_order(
    action: Action,
) -> None:
    gates = ChunkGates()
    harness = Harness(gates.respond_limits)

    with pytest.raises(AiDailyLimitReached) as caught:
        async with asyncio.timeout(_PROMPT_SECONDS):
            await action(harness)

    assert caught.value.limit is AiDailyLimit.USER_SHARE
    assert gates.cancelled == []
    assert sorted(gates.released) == [1, 200]
