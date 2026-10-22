"""A failed or unterminated upstream stream ends the chat turn as failed.

Purpose:
    Prove that the real ``OpenAIChatStreamProvider`` and the real chat handler,
    given a streamed body that delivers text and then fails or stops without
    ``response.completed``, keep the partial text, persist a failed turn and
    send ``done(reason="error")``, never a successful stop.

Relationships:
    Exercises ``infrastructure.llm.openai.chat_stream_provider`` through
    ``tests.fixtures.editor_chat_handler_harness`` over ``RecordingDoor``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.infrastructure.llm.openai.chat_stream_provider import OpenAIChatStreamProvider
from skriptoteket.protocols.llm import (
    EditorChatCommand,
    EditorChatDeltaEvent,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
    LLMChatRequest,
)
from tests.fixtures.editor_chat_handler_harness import make_chat_handler_harness
from tests.fixtures.identity_fixtures import make_user
from tests.unit.llm_door_fakes import DoorSent, RecordingDoor, sse_reply

pytestmark = pytest.mark.unit

_DELTA: tuple[str, JsonValue] = (
    "response.output_text.delta",
    {"type": "response.output_text.delta", "delta": "partial"},
)
_FAILED: tuple[str, JsonValue] = (
    "response.failed",
    {
        "type": "response.failed",
        "response": {"status": "failed", "error": {"code": "server_error", "message": "boom"}},
    },
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "events",
    [[_DELTA, _FAILED], [_DELTA]],
    ids=["response_failed", "eof_without_terminal"],
)
async def test_unsuccessful_upstream_end_fails_the_turn_and_keeps_the_partial_text(
    events: list[tuple[str, JsonValue]],
) -> None:
    user_id = uuid4()
    tool_id = uuid4()
    harness = make_chat_handler_harness(tool_id=tool_id, user_id=user_id)
    door = RecordingDoor(lambda sent: sse_reply(events))
    provider = OpenAIChatStreamProvider(settings=Settings(), door=door)

    def stream_chat(
        *, request: LLMChatRequest, system_prompt: str, caller: AiDoorCaller
    ) -> AsyncIterator[str]:
        return provider.stream_chat(request=request, system_prompt=system_prompt, caller=caller)

    harness.provider.stream_chat.side_effect = stream_chat

    streamed = [
        event
        async for event in harness.handler.stream(
            actor=make_user(role=Role.ADMIN, user_id=user_id),
            command=EditorChatCommand(tool_id=tool_id, message="Hej"),
        )
    ]

    assert [event.event for event in streamed] == ["meta", "delta", "done"]
    delta = streamed[1]
    assert isinstance(delta, EditorChatDeltaEvent) and delta.data.text == "partial"
    done = streamed[-1]
    assert isinstance(done, EditorChatDoneEvent)
    assert isinstance(done.data, EditorChatDoneEnabledData) and done.data.reason == "error"
    status_call = harness.turns.update_status.call_args.kwargs
    assert status_call["turn_id"] == harness.turn_id
    assert status_call["status"] == "failed"
    assert status_call["failure_outcome"] == "error"
    assert (
        harness.messages.update_message_content_if_pending_turn.call_args.kwargs["content"]
        == "partial"
    )
    assert harness.guard.held == set()
    assert len(door.sent) == 1 and isinstance(door.sent[0], DoorSent)
