"""Door-boundary tests for the three script-editor providers.

Purpose:
    Prove inline completion, chat ops and chat streaming send their Responses
    bodies only through the LLM provider door with the action's caller, on the
    editor models and efforts, and map every door outcome to
    ``EditorLlmProviderError`` while daily-limit refusals propagate untouched.

Relationships:
    Exercises ``infrastructure.llm.openai.{inline_completion,chat_ops,chat_stream}_provider``
    against ``tests.unit.llm_door_fakes.RecordingDoor``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.config import Settings
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    AiOverageAuthority,
)
from skriptoteket.infrastructure.llm.openai.chat_ops_provider import OpenAIChatOpsProvider
from skriptoteket.infrastructure.llm.openai.chat_stream_provider import OpenAIChatStreamProvider
from skriptoteket.infrastructure.llm.openai.edit_ops_text_format import (
    EDIT_OPS_PATCH_ONLY_RESPONSES_TEXT_FORMAT,
)
from skriptoteket.infrastructure.llm.openai.inline_completion_provider import (
    OpenAIInlineCompletionProvider,
)
from skriptoteket.protocols.llm import ChatMessage, LLMChatRequest, LLMCompletionRequest
from skriptoteket.protocols.llm.common import EditorLlmProviderError
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorReply,
    DoorRequestFailed,
    DoorTimeout,
)
from tests.unit.llm_door_fakes import (
    DoorResponder,
    DoorSent,
    RecordingDoor,
    json_reply,
    limit_refusal,
    sse_reply,
)

pytestmark = pytest.mark.unit

_OUTPUT_PAYLOAD: dict[str, JsonValue] = {
    "status": "completed",
    "output": [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "done"}],
        }
    ],
}
_CHAT_REQUEST = LLMChatRequest(messages=[ChatMessage(role="user", content="hello")])
_COMPLETION_REQUEST = LLMCompletionRequest(prefix="def f(", suffix=")", active_file="tool.py")

_FORBIDDEN_KEYS = {
    "temperature",
    "prompt_cache_key",
    "prompt_cache_retention",
    "cache_prompt",
    "grammar",
    "response_format",
    "messages",
}

_Call = Callable[[RecordingDoor, AiDoorCaller], Awaitable[object]]


async def _complete(door: RecordingDoor, caller: AiDoorCaller) -> object:
    provider = OpenAIInlineCompletionProvider(settings=Settings(), door=door)
    return await provider.complete_inline(
        request=_COMPLETION_REQUEST, system_prompt="sys", caller=caller
    )


async def _chat_ops(door: RecordingDoor, caller: AiDoorCaller) -> object:
    provider = OpenAIChatOpsProvider(settings=Settings(), door=door)
    return await provider.complete_chat_ops(
        request=_CHAT_REQUEST, system_prompt="sys", caller=caller
    )


async def _chat_stream(door: RecordingDoor, caller: AiDoorCaller) -> object:
    provider = OpenAIChatStreamProvider(settings=Settings(), door=door)
    return [
        delta
        async for delta in provider.stream_chat(
            request=_CHAT_REQUEST, system_prompt="sys", caller=caller
        )
    ]


def _caller() -> AiDoorCaller:
    return AiDoorCaller(
        user_id=uuid4(), exempt=False, authority=AiOverageAuthority.JOB_CONTINUATION
    )


def _stream_events(*deltas: str) -> DoorReply:
    events: list[tuple[str, JsonValue]] = [
        ("response.output_text.delta", {"type": "response.output_text.delta", "delta": delta})
        for delta in deltas
    ]
    events.append(("response.completed", {"type": "response.completed"}))
    return sse_reply(events)


def _respond_with(reply: DoorReply) -> DoorResponder:
    def respond(sent: DoorSent) -> DoorReply:
        return reply

    return respond


def _error_reply(status_code: int, body: JsonValue) -> DoorReply:
    return json_reply(body, status_code=status_code)


def _assert_responses_body(
    sent: DoorSent, *, model: str, effort: str, caller: AiDoorCaller, stream: bool
) -> None:
    assert sent.operation is DoorOperation.RESPONSES
    assert sent.caller is caller
    assert sent.payload["model"] == model
    assert sent.payload["reasoning"] == {"effort": effort}
    assert sent.payload["stream"] is stream
    assert _FORBIDDEN_KEYS.isdisjoint(sent.payload)


@pytest.mark.asyncio
async def test_completion_sends_one_luna_responses_call_for_the_caller() -> None:
    door = RecordingDoor(_respond_with(json_reply(_OUTPUT_PAYLOAD)))
    caller = _caller()

    response = await OpenAIInlineCompletionProvider(settings=Settings(), door=door).complete_inline(
        request=_COMPLETION_REQUEST, system_prompt="sys", caller=caller
    )

    assert response.completion == "done"
    assert response.finish_reason == "stop"
    assert len(door.sent) == 1
    sent = door.sent[0]
    _assert_responses_body(sent, model="gpt-6-luna", effort="none", caller=caller, stream=False)
    assert sent.caller.user_id == caller.user_id
    assert sent.payload["store"] is False
    assert sent.payload["truncation"] == "auto"
    assert "stop" not in sent.payload
    assert sent.payload["instructions"] == "sys"
    assert sent.timeout_seconds == Settings().LLM_COMPLETION_TIMEOUT_SECONDS
    prompt = str(sent.payload["input"])
    assert "<PREFIX>" in prompt and "def f(" in prompt and "<SUFFIX>" in prompt


@pytest.mark.asyncio
async def test_chat_ops_sends_sol_low_with_the_patch_only_text_format() -> None:
    door = RecordingDoor(_respond_with(json_reply(_OUTPUT_PAYLOAD)))
    caller = _caller()

    response = await OpenAIChatOpsProvider(settings=Settings(), door=door).complete_chat_ops(
        request=_CHAT_REQUEST, system_prompt="sys", caller=caller
    )

    assert response.content == "done"
    assert response.raw_payload == _OUTPUT_PAYLOAD
    assert len(door.sent) == 1
    sent = door.sent[0]
    _assert_responses_body(sent, model="gpt-6.1-sol", effort="low", caller=caller, stream=False)
    text = sent.payload["text"]
    assert isinstance(text, dict)
    text_format = text["format"]
    assert isinstance(text_format, dict)
    assert text_format["type"] == "json_schema"
    assert text_format["name"] == EDIT_OPS_PATCH_ONLY_RESPONSES_TEXT_FORMAT["name"]
    assert text_format["schema"] == EDIT_OPS_PATCH_ONLY_RESPONSES_TEXT_FORMAT["schema"]
    assert sent.timeout_seconds == Settings().LLM_CHAT_OPS_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_chat_streams_sol_low_and_relays_every_delta() -> None:
    door = RecordingDoor(_respond_with(_stream_events("Hel", "lo ", "world")))
    caller = _caller()

    deltas = await _chat_stream(door, caller)

    assert deltas == ["Hel", "lo ", "world"]
    assert len(door.sent) == 1
    _assert_responses_body(
        door.sent[0], model="gpt-6.1-sol", effort="low", caller=caller, stream=True
    )
    assert door.sent[0].timeout_seconds == Settings().LLM_CHAT_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_chat_stream_stops_at_the_done_marker() -> None:
    body = (
        'event: response.output_text.delta\ndata: {"delta": "a"}\n\n'
        "data: [DONE]\n\n"
        'event: response.output_text.delta\ndata: {"delta": "never"}\n\n'
    )
    reply = DoorReply(status_code=200, headers={}, body=body.encode())
    door = RecordingDoor(_respond_with(reply))

    assert await _chat_stream(door, _caller()) == ["a"]


@pytest.mark.asyncio
@pytest.mark.parametrize("call", [_complete, _chat_ops, _chat_stream])
async def test_user_share_refusal_propagates_from_every_provider(call: _Call) -> None:
    door = RecordingDoor(limit_refusal(AiDailyLimit.USER_SHARE))

    with pytest.raises(AiDailyLimitReached) as raised:
        await call(door, _caller())

    assert raised.value.limit is AiDailyLimit.USER_SHARE


@pytest.mark.asyncio
@pytest.mark.parametrize("call", [_complete, _chat_ops, _chat_stream])
async def test_context_length_exceeded_maps_to_context_window_exceeded(call: _Call) -> None:
    reply = _error_reply(400, {"error": {"code": "context_length_exceeded", "message": "big"}})
    door = RecordingDoor(_respond_with(reply))

    with pytest.raises(EditorLlmProviderError) as raised:
        await call(door, _caller())

    assert raised.value.kind == "context_window_exceeded"
    assert raised.value.status_code == 400
    assert raised.value.detail is not None and "context_length_exceeded" in raised.value.detail


@pytest.mark.asyncio
@pytest.mark.parametrize("call", [_complete, _chat_ops, _chat_stream])
async def test_other_status_maps_to_http_status_with_truncated_detail(call: _Call) -> None:
    reply = DoorReply(status_code=503, headers={}, body=b"x" * 5000)
    door = RecordingDoor(_respond_with(reply))

    with pytest.raises(EditorLlmProviderError) as raised:
        await call(door, _caller())

    assert raised.value.kind == "http_status"
    assert raised.value.status_code == 503
    assert raised.value.detail == "x" * 2000


@pytest.mark.asyncio
@pytest.mark.parametrize("call", [_complete, _chat_ops, _chat_stream])
async def test_door_capacity_429_maps_to_http_status(call: _Call) -> None:
    reply = _error_reply(429, {"error": {"code": "capacity"}})
    door = RecordingDoor(_respond_with(reply))

    with pytest.raises(EditorLlmProviderError) as raised:
        await call(door, _caller())

    assert (raised.value.kind, raised.value.status_code) == ("http_status", 429)


@pytest.mark.asyncio
@pytest.mark.parametrize("call", [_complete, _chat_ops, _chat_stream])
@pytest.mark.parametrize(
    ("raised_by_door", "kind"),
    [(DoorTimeout, "timeout"), (DoorRequestFailed, "request_failed")],
)
async def test_door_transport_failures_map_to_their_kinds(
    call: _Call, raised_by_door: type[Exception], kind: str
) -> None:
    def respond(sent: DoorSent) -> DoorReply:
        raise raised_by_door()

    with pytest.raises(EditorLlmProviderError) as raised:
        await call(RecordingDoor(respond), _caller())

    assert raised.value.kind == kind
    assert raised.value.status_code is None


@pytest.mark.asyncio
@pytest.mark.parametrize("call", [_complete, _chat_ops])
@pytest.mark.parametrize(
    "body",
    [b"not json", b"[1, 2]", b'{"status": "completed"}'],
)
async def test_unparseable_answers_map_to_invalid_response(call: _Call, body: bytes) -> None:
    reply = DoorReply(status_code=200, headers={}, body=body)
    door = RecordingDoor(_respond_with(reply))

    with pytest.raises(EditorLlmProviderError) as raised:
        await call(door, _caller())

    assert raised.value.kind == "invalid_response"


@pytest.mark.asyncio
async def test_stream_error_chunk_maps_to_invalid_response_after_earlier_deltas() -> None:
    reply = sse_reply(
        [
            ("response.output_text.delta", {"type": "response.output_text.delta", "delta": "a"}),
            ("error", {"error": {"message": "boom"}}),
        ]
    )
    door = RecordingDoor(_respond_with(reply))
    provider = OpenAIChatStreamProvider(settings=Settings(), door=door)
    received: list[str] = []

    with pytest.raises(EditorLlmProviderError) as raised:
        async for delta in provider.stream_chat(
            request=_CHAT_REQUEST, system_prompt="sys", caller=_caller()
        ):
            received.append(delta)

    assert received == ["a"]
    assert raised.value.kind == "invalid_response"
    assert raised.value.detail is not None and "boom" in raised.value.detail
