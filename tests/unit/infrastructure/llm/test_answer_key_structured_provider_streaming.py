"""Synthetic SSE proof for structured observation, terminal results and settlement."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMProviderError,
)
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.protocols.llm_door import DoorReply
from tests.unit.infrastructure.llm.door.door_client_support import make_door_client
from tests.unit.infrastructure.llm.test_answer_key_structured_provider_door import (
    _profile,
    _request,
)
from tests.unit.llm_door_fakes import (
    RecordingDoor,
    fixture_caller,
    json_reply,
    sse_reply,
)


def _event(kind: str, **fields: JsonValue) -> tuple[str, JsonValue]:
    return kind, {"type": kind, **fields}


def _terminal(status: str = "completed", text: str = '{"answer":"2"}') -> tuple[str, JsonValue]:
    return _event(
        f"response.{status}",
        response={
            "status": status,
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 31, "output_tokens": 17, "total_tokens": 48},
        },
    )


async def test_fragmented_sse_observes_text_before_terminal_and_retains_final_result() -> None:
    observed: list[str] = []
    content: dict[str, JsonValue] = {"nested": [{"text": 'räv \\"quoted"'}, [1, {"x": True}]]}
    text = json.dumps(content, ensure_ascii=False)
    deltas = [text[:8], text[8:27], text[27:]]
    caller = fixture_caller(exempt=False)

    async def on_text(delta: str) -> None:
        observed.append(delta)

    class FragmentedBody(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            for delta in deltas:
                frame = sse_reply([_event("response.output_text.delta", delta=delta)]).body
                # Exercise httpx's UTF-8 and line framing across arbitrary byte boundaries.
                for byte in frame:
                    yield bytes([byte])
            assert observed == deltas  # Network has not emitted a terminal event yet.
            # The terminal response, not accumulated observation, supplies final content.
            yield sse_reply([_terminal(text=json.dumps({"final": content}))]).body
            yield sse_reply(
                [_event("huleedu.door.charge", charge_kind="overage", charge_usd_micros=125)]
            ).body

    door = make_door_client(
        httpx.MockTransport(lambda request: httpx.Response(200, stream=FragmentedBody()))
    )
    response = await OpenAIAnswerKeyStructuredProvider(
        door=door, timeout_seconds=5
    ).complete_structured(request=_request(), profile=_profile(), caller=caller, on_text=on_text)

    assert observed == deltas
    assert response.content == {"final": content}
    assert response.finish_reason == "completed"
    assert response.usage.prompt_tokens == 31
    assert response.usage.completion_tokens == 17
    assert response.usage.total_tokens == 48
    assert caller.overage_usd_micros == 125


async def test_observer_selects_stream_but_no_observer_keeps_complete_body_path() -> None:
    door = RecordingDoor(
        lambda sent: (
            sse_reply([_terminal()])
            if sent.payload["stream"]
            else json_reply({"status": "completed", "output_text": '{"answer":"2"}'})
        )
    )
    provider = OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5)

    async def on_text(delta: str) -> None:
        raise AssertionError("no text delta was sent")

    streamed = await provider.complete_structured(
        request=_request(), profile=_profile(), caller=fixture_caller(), on_text=on_text
    )
    buffered = await provider.complete_structured(
        request=_request(), profile=_profile(), caller=fixture_caller()
    )
    assert streamed.content == buffered.content == {"answer": "2"}
    assert [sent.payload["stream"] for sent in door.sent] == [True, False]


@pytest.mark.parametrize(
    ("events", "code"),
    [
        ([_event("response.failed", response={"status": "failed"})], "provider_request_failed"),
        ([_event("error", message="upstream failed")], "provider_request_failed"),
        ([], "provider_request_failed"),
        ([_event("response.refusal.delta", delta="No"), _terminal(text="")], "provider_refusal"),
        ([_terminal(text='{"unfinished":')], "provider_content_not_json"),
        ([_terminal(status="incomplete", text='{"unfinished":')], "provider_content_not_json"),
        (
            [_event("response.completed", response={"status": "completed", "refusal": "No"})],
            "provider_refusal",
        ),
        ([_event("response.completed", response={"status": "failed"})], "provider_request_failed"),
    ],
)
async def test_terminal_failures_preserve_observed_text_and_settle_late_charge(
    events: list[tuple[str, JsonValue]], code: str
) -> None:
    observed: list[str] = []
    caller = fixture_caller(exempt=False)
    door = RecordingDoor(
        lambda sent: sse_reply(
            [
                _event("response.output_text.delta", delta='{"unfinished":'),
                *events,
                _event("huleedu.door.charge", charge_kind="overage", charge_usd_micros=9),
            ]
        )
    )

    async def on_text(delta: str) -> None:
        observed.append(delta)

    with pytest.raises(StructuredLLMProviderError) as caught:
        await OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5).complete_structured(
            request=_request(), profile=_profile(), caller=caller, on_text=on_text
        )
    assert caught.value.failure_code.value == code
    assert observed == ['{"unfinished":']
    assert caller.overage_usd_micros == 9


async def test_incomplete_terminal_uses_ordinary_content_and_finish_status() -> None:
    door = RecordingDoor(lambda sent: sse_reply([_terminal(status="incomplete")]))

    async def on_text(delta: str) -> None:
        pass

    result = await OpenAIAnswerKeyStructuredProvider(
        door=door, timeout_seconds=5
    ).complete_structured(
        request=_request(), profile=_profile(), caller=fixture_caller(), on_text=on_text
    )
    assert result.content == {"answer": "2"}
    assert result.finish_reason == "incomplete"
    assert result.usage.total_tokens == 48


@pytest.mark.parametrize("timeout", [True, False])
async def test_disconnect_after_observation_remains_a_transport_failure(timeout: bool) -> None:
    observed: list[str] = []

    class DisconnectedBody(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield sse_reply([_event("response.output_text.delta", delta="partial")]).body
            if timeout:
                raise httpx.ReadTimeout("stalled")
            raise httpx.ReadError("disconnected")

    door = make_door_client(
        httpx.MockTransport(lambda request: httpx.Response(200, stream=DisconnectedBody()))
    )

    async def on_text(delta: str) -> None:
        observed.append(delta)

    with pytest.raises(StructuredLLMProviderError) as caught:
        await OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5).complete_structured(
            request=_request(), profile=_profile(), caller=fixture_caller(), on_text=on_text
        )
    assert caught.value.failure_code is (
        StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT
        if timeout
        else StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED
    )
    assert observed == ["partial"]


async def test_sse_multiline_data_comments_and_unterminated_tail() -> None:
    observed: list[str] = []
    wire = (
        (
            ": heartbeat\r\nevent: response.output_text.delta\r\n"
            'data: {"type":"response.output_text.delta",\r\n'
            'data: "delta":"ok"}\r\n\r\n'
        ).encode()
        + sse_reply([_terminal()]).body
        + b'event: response.output_text.delta\ndata: {"delta":"lost"}'
    )
    door = RecordingDoor(lambda sent: DoorReply(status_code=200, headers={}, body=wire))

    async def on_text(delta: str) -> None:
        observed.append(delta)

    result = await OpenAIAnswerKeyStructuredProvider(
        door=door, timeout_seconds=5
    ).complete_structured(
        request=_request(), profile=_profile(), caller=fixture_caller(), on_text=on_text
    )
    assert result.content == {"answer": "2"}
    assert observed == ["ok"]
