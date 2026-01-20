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
