"""A dropped editor chat connection closes the whole stream chain at once (41-01-02 F1).

The route, the real handler, orchestrator, ``OpenAIChatStreamProvider`` and
``HuleEduLlmDoorClient`` (one process slot) run under a real ``StreamingResponse``
call. The upstream body is an observable byte stream. The client disconnect
arrives while ``send`` is suspended on a yielded event, or while the stream waits
for the next upstream delta. The assertions run as soon as the response call
returns, before any garbage collection can close an abandoned generator.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable, Coroutine, MutableMapping
from dataclasses import dataclass, replace
from typing import Literal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.responses import Response
from starlette.requests import ClientDisconnect

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import AiDoorCaller, AiOverageAuthority
from skriptoteket.infrastructure.llm.door.client import DoorBounds, HuleEduLlmDoorClient
from skriptoteket.infrastructure.llm.openai.chat_stream_provider import OpenAIChatStreamProvider
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.llm_door import DoorOperation
from skriptoteket.web.api.v1.editor.chat import stream_editor_chat
from skriptoteket.web.api.v1.editor.models.requests import EditorChatRequest
from tests.fixtures.editor_chat_handler_harness import ChatHandlerHarness, make_chat_handler_harness
from tests.fixtures.identity_fixtures import make_user

_DELTA = (
    b"event: response.output_text.delta\n"
    b'data: {"type": "response.output_text.delta", "delta": "hej"}\n\n'
)
_META_BODY = 1
_DELTA_BODY = 2
_TIMEOUT_SECONDS = 5

SpecVersion = Literal["2.3", "2.4"]
Message = MutableMapping[str, object]


class _ObservedUpstream(httpx.AsyncByteStream):
    """One upstream answer: a delta, then silence until the test ends."""

    def __init__(self) -> None:
        self.closed = False
        self.waiting_for_next_delta = asyncio.Event()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield _DELTA
        self.waiting_for_next_delta.set()
        await asyncio.Event().wait()

    async def aclose(self) -> None:
        self.closed = True


class _NoSleep:
    async def sleep(self, seconds: float) -> None:
        return None


@dataclass(slots=True)
class _Rig:
    harness: ChatHandlerHarness
    door: HuleEduLlmDoorClient
    upstream: _ObservedUpstream
    status_updates: list[dict[str, object]]
    tool_id: UUID
    user_id: UUID

    async def open_response(self) -> Response:
        response = await stream_editor_chat(
            tool_id=self.tool_id,
            payload=EditorChatRequest(message="Hej"),
            handler=self.harness.handler,
            maintainers=MagicMock(spec=ToolMaintainerRepositoryProtocol),
            user=make_user(role=Role.ADMIN, user_id=self.user_id),
        )
        return response

    async def second_door_call_status(self) -> int:
        reply = await self.door.send(
            operation=DoorOperation.RESPONSES,
            payload={"model": "gpt-6.1-luna", "input": "hej"},
            caller=AiDoorCaller(
                user_id=uuid4(), exempt=True, authority=AiOverageAuthority.JOB_CONTINUATION
            ),
            timeout_seconds=_TIMEOUT_SECONDS,
        )
        return reply.status_code


def _build_rig() -> _Rig:
    tool_id = uuid4()
    user_id = uuid4()
    harness = make_chat_handler_harness(tool_id=tool_id, user_id=user_id)
    upstream = _ObservedUpstream()
    opened: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        opened.append(request)
        if len(opened) == 1:
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=upstream
            )
        return httpx.Response(200, json={"status": "completed", "output": []})

    settings = Settings(LLM_CHAT_ENABLED=True, HULEEDU_INTERNAL_API_KEY="test-door-key")
    door = HuleEduLlmDoorClient(
        client=httpx.AsyncClient(transport=httpx.MockTransport(answer)),
        base_url="http://door.test:8080",
        internal_api_key="internal-key",
        job_overage_cap_usd_micros=1_000_000,
        sleeper=_NoSleep(),
        bounds=replace(DoorBounds.from_settings(settings), max_in_flight=1, slot_wait_seconds=0.05),
    )
    harness.provider.stream_chat.side_effect = OpenAIChatStreamProvider(
        settings=settings, door=door
    ).stream_chat

    # Persistence ports that yield to the loop, as database calls do. A status update
    # counts only once it has completed.
    status_updates: list[dict[str, object]] = []

    async def record_status(**kwargs: object) -> None:
        await asyncio.sleep(0)
        status_updates.append(dict(kwargs))

    async def store_content(**_: object) -> bool:
        await asyncio.sleep(0)
        return True

    harness.turns.update_status.side_effect = record_status
    harness.messages.update_message_content_if_pending_turn.side_effect = store_content
    return _Rig(
        harness=harness,
        door=door,
        upstream=upstream,
        status_updates=status_updates,
        tool_id=tool_id,
        user_id=user_id,
    )


def _http_scope(spec_version: SpecVersion) -> dict[str, object]:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": spec_version},
        "method": "POST",
        "path": "/api/v1/editor/tools/chat",
        "headers": [],
    }


class _Client:
    """An ASGI peer whose ``send`` hangs on one body event, then drops the connection."""

    def __init__(self, *, spec_version: SpecVersion, hang_on_body: int | None) -> None:
        self.spec_version: SpecVersion = spec_version
        self._hang_on_body = hang_on_body
        self._bodies = 0
        self.send_hanging = asyncio.Event()

    async def receive_until(self, event: asyncio.Event) -> Message:
        await event.wait()
        return {"type": "http.disconnect"}

    async def send(self, message: Message) -> None:
        if message["type"] != "http.response.body":
            return
        self._bodies += 1
        if self._bodies != self._hang_on_body:
            return
        self.send_hanging.set()
        if self.spec_version == "2.4":
            raise OSError("the client went away")
        await asyncio.Event().wait()


async def _call(
    rig: _Rig, client: _Client, *, disconnect_signal: asyncio.Event
) -> Callable[[], Coroutine[None, None, None]]:
    response = await rig.open_response()

    async def receive() -> Message:
        return await client.receive_until(disconnect_signal)

    async def run() -> None:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            await response(_http_scope(client.spec_version), receive, client.send)

    return run


async def _assert_chain_closed(rig: _Rig) -> None:
    # Checked straight after the response call, with no gc.collect() in between.
    assert rig.upstream.closed, "the upstream HTTP body stayed open"
    assert [(u["status"], u["failure_outcome"]) for u in rig.status_updates] == [
        ("cancelled", "cancelled")
    ], "the turn was not finalized as cancelled"
    assert rig.harness.guard.held == set(), "the chat in-flight guard stayed held"
    assert await rig.second_door_call_status() == 200, "the door slot stayed held"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("spec_version", ["2.3", "2.4"])
@pytest.mark.parametrize(
    "hang_on_body", [_META_BODY, _DELTA_BODY], ids=["after_meta", "after_delta"]
)
async def test_disconnect_while_send_is_suspended_closes_the_whole_chain(
    spec_version: SpecVersion, hang_on_body: int
) -> None:
    rig = _build_rig()
    client = _Client(spec_version=spec_version, hang_on_body=hang_on_body)
    run = await _call(rig, client, disconnect_signal=client.send_hanging)

    if spec_version == "2.4":
        with pytest.raises(ClientDisconnect):
            await run()
    else:
        await run()

    assert client.send_hanging.is_set()
    await _assert_chain_closed(rig)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("by", ["disconnect_message", "task_cancelled"])
async def test_disconnect_while_waiting_for_the_next_upstream_delta_closes_the_chain(
    by: Literal["disconnect_message", "task_cancelled"],
) -> None:
    rig = _build_rig()
    client = _Client(spec_version="2.3", hang_on_body=None)
    run = await _call(rig, client, disconnect_signal=rig.upstream.waiting_for_next_delta)

    if by == "disconnect_message":
        await run()
    else:
        task = asyncio.create_task(run())
        await asyncio.wait_for(rig.upstream.waiting_for_next_delta.wait(), _TIMEOUT_SECONDS)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    assert rig.upstream.waiting_for_next_delta.is_set()
    await _assert_chain_closed(rig)
