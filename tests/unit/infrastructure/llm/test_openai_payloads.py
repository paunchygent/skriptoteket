from __future__ import annotations

import pytest

from skriptoteket.infrastructure.llm.openai.payloads import build_responses_payload
from skriptoteket.infrastructure.llm.openai.types import ResponsesJsonSchemaTextFormat


@pytest.mark.unit
def test_build_responses_payload_maps_messages_and_instructions() -> None:
    payload = build_responses_payload(
        model="gpt-6.1-sol",
        messages=[{"role": "user", "content": "hi"}],
        instructions="sys",
        max_tokens=123,
        reasoning_effort="low",
        text_verbosity="low",
        stream=False,
    )

    assert payload == {
        "model": "gpt-6.1-sol",
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "hi"}],
            }
        ],
        "stream": False,
        "max_output_tokens": 123,
        "instructions": "sys",
        "reasoning": {"effort": "low"},
        "text": {"verbosity": "low"},
    }


@pytest.mark.unit
def test_build_responses_payload_maps_assistant_messages_as_output_text() -> None:
    payload = build_responses_payload(
        model="gpt-6.1-sol",
        messages=[
            {"role": "assistant", "content": "previous"},
            {"role": "user", "content": "hi"},
        ],
        instructions="sys",
        max_tokens=123,
        reasoning_effort="low",
        text_verbosity=None,
        stream=True,
    )

    assert payload["stream"] is True
    assert payload["input"] == [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "previous"}],
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "hi"}],
        },
    ]
    assert "text" not in payload


@pytest.mark.unit
def test_build_responses_payload_omits_unset_options_and_never_sends_temperature() -> None:
    payload = build_responses_payload(
        model="gpt-6-luna",
        messages=[{"role": "user", "content": "hi"}],
        instructions=None,
        max_tokens=64,
        reasoning_effort=None,
        text_verbosity=None,
        stream=False,
    )

    assert set(payload) == {"model", "input", "stream", "max_output_tokens"}


@pytest.mark.unit
def test_build_responses_payload_sends_store_truncation_and_no_stop() -> None:
    # The Responses API has no stop parameter; completion normalization strips
    # a trailing code fence instead.
    payload = build_responses_payload(
        model="gpt-6-luna",
        messages=[{"role": "user", "content": "hi"}],
        instructions="sys",
        max_tokens=64,
        reasoning_effort="none",
        text_verbosity="low",
        stream=False,
        store=False,
        truncation="auto",
    )

    assert payload["store"] is False
    assert payload["truncation"] == "auto"
    assert "stop" not in payload
    assert payload["reasoning"] == {"effort": "none"}


@pytest.mark.unit
def test_build_responses_payload_merges_text_format_and_verbosity() -> None:
    payload = build_responses_payload(
        model="gpt-6.1-sol",
        messages=[{"role": "user", "content": "hi"}],
        instructions="sys",
        max_tokens=64,
        reasoning_effort="low",
        text_verbosity="high",
        stream=False,
        text_format={"type": "json_schema", "name": "test", "schema": {}, "strict": True},
    )

    assert payload["text"] == {
        "verbosity": "high",
        "format": {"type": "json_schema", "name": "test", "schema": {}, "strict": True},
    }


@pytest.mark.unit
def test_build_responses_payload_rejects_json_schema_format_without_name() -> None:
    empty_name_format: ResponsesJsonSchemaTextFormat = {
        "type": "json_schema",
        "name": "",
        "schema": {},
    }

    with pytest.raises(ValueError):
        build_responses_payload(
            model="gpt-6.1-sol",
            messages=[{"role": "user", "content": "hi"}],
            instructions="sys",
            max_tokens=64,
            reasoning_effort="low",
            text_verbosity="high",
            stream=False,
            text_format=empty_name_format,
        )
