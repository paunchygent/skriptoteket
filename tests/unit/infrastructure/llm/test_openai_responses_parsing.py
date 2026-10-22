from __future__ import annotations

import pytest

from skriptoteket.infrastructure.llm.openai.parsing import (
    extract_response_output_text,
    extract_response_stream_delta,
)


@pytest.mark.unit
def test_extract_response_output_text_from_message_items() -> None:
    payload = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Hello"}],
            }
        ],
    }

    text, finish_reason = extract_response_output_text(payload)

    assert text == "Hello"
    assert finish_reason == "stop"


@pytest.mark.unit
def test_extract_response_output_text_maps_incomplete_reason() -> None:
    payload = {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "Hi"}],
            }
        ],
    }

    text, finish_reason = extract_response_output_text(payload)

    assert text == "Hi"
    assert finish_reason == "length"


@pytest.mark.unit
def test_extract_response_output_text_prefers_output_text_field() -> None:
    payload = {
        "status": "completed",
        "output_text": "Direct",
        "output": [],
    }

    text, finish_reason = extract_response_output_text(payload)

    assert text == "Direct"
    assert finish_reason == "stop"


@pytest.mark.unit
def test_extract_response_stream_delta_emits_delta_and_done() -> None:
    delta, done = extract_response_stream_delta(
        {"type": "response.output_text.delta", "delta": "Hello"},
        event_type=None,
    )

    assert delta == "Hello"
    assert done is False

    delta, done = extract_response_stream_delta(
        {"type": "response.completed"},
        event_type=None,
    )

    assert delta == ""
    assert done is True


@pytest.mark.unit
@pytest.mark.parametrize(
    ("payload", "event_type", "fragment"),
    [
        (
            {"type": "response.failed", "response": {"error": {"message": "nested-boom"}}},
            None,
            "nested-boom",
        ),
        (
            {
                "type": "response.incomplete",
                "response": {"incomplete_details": {"reason": "max_output_tokens"}},
            },
            None,
            "max_output_tokens",
        ),
        ({"message": "plain"}, "response.failed", "response.failed"),
        ({"type": "error", "message": "stream-boom"}, None, "stream-boom"),
        ({"error": {"message": "untyped-boom"}}, "error", "untyped-boom"),
        ({"type": "response.output_text.delta", "delta": 7}, None, "not text"),
        (
            {"type": "response.completed", "response": {"status": "failed"}},
            None,
            "status failed",
        ),
    ],
)
def test_extract_response_stream_delta_rejects_every_unsuccessful_event(
    payload: dict[str, object], event_type: str | None, fragment: str
) -> None:
    with pytest.raises(ValueError, match=fragment):
        extract_response_stream_delta(payload, event_type=event_type)


@pytest.mark.unit
def test_extract_response_stream_delta_ignores_progress_events() -> None:
    assert extract_response_stream_delta({"type": "response.created"}) == ("", False)
