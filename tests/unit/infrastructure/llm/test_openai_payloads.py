from __future__ import annotations

from typing import cast

import pytest

from skriptoteket.infrastructure.llm.openai.payloads import (
    build_chat_payload,
    build_responses_payload,
)
from skriptoteket.infrastructure.llm.openai.types import (
    ResponsesInputText,
    ResponsesOutputText,
    ResponsesTextFormat,
)


@pytest.mark.unit
def test_build_chat_payload_uses_classic_max_tokens_for_non_gpt5() -> None:
    payload = build_chat_payload(
        model="Devstral-Small-2-24B",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="medium",
        stream=False,
    )

    assert payload["max_tokens"] == 123
    assert payload["temperature"] == 0.2
    assert "max_completion_tokens" not in payload


@pytest.mark.unit
def test_build_chat_payload_uses_max_completion_tokens_for_gpt5() -> None:
    payload = build_chat_payload(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="medium",
        stream=False,
    )

    assert payload["max_completion_tokens"] == 123
    assert payload["reasoning_effort"] == "medium"
    assert "max_tokens" not in payload


@pytest.mark.unit
def test_build_chat_payload_omits_prompt_cache_params_when_disallowed() -> None:
    payload = build_chat_payload(
        model="Devstral-Small-2-24B",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort=None,
        stream=False,
        cache_prompt=True,
        prompt_cache_retention="24h",
        prompt_cache_key="key",
        allow_prompt_cache_params=False,
    )

    assert payload["cache_prompt"] is True
    assert "prompt_cache_retention" not in payload
    assert "prompt_cache_key" not in payload


@pytest.mark.unit
def test_build_chat_payload_omits_stop_for_gpt5_nano() -> None:
    payload = build_chat_payload(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="minimal",
        stream=False,
        stop=["\n```"],
    )

    assert "stop" not in payload


@pytest.mark.unit
def test_build_chat_payload_includes_stop_for_supported_models() -> None:
    payload = build_chat_payload(
        model="gpt-5.2",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="low",
        stream=False,
        stop=["\n```"],
    )

    assert payload["stop"] == ["\n```"]


@pytest.mark.unit
def test_build_chat_payload_omits_prompt_cache_retention_for_gpt5_nano() -> None:
    payload = build_chat_payload(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="minimal",
        stream=False,
        prompt_cache_retention="24h",
        prompt_cache_key="key",
        allow_prompt_cache_params=True,
    )

    assert "prompt_cache_retention" not in payload
    assert "prompt_cache_key" not in payload


@pytest.mark.unit
def test_build_chat_payload_includes_prompt_cache_retention_for_supported_models() -> None:
    payload = build_chat_payload(
        model="gpt-5.1-codex-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="low",
        stream=False,
        prompt_cache_retention="24h",
        prompt_cache_key="key",
        allow_prompt_cache_params=True,
    )

    assert payload["prompt_cache_retention"] == "24h"
    assert payload["prompt_cache_key"] == "key"


@pytest.mark.unit
def test_build_responses_payload_maps_messages_and_instructions() -> None:
    payload = build_responses_payload(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hi"}],
        instructions="sys",
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="minimal",
        text_verbosity="low",
        stream=False,
    )

    assert payload["instructions"] == "sys"
    assert payload["max_output_tokens"] == 123
    assert "reasoning" in payload
    assert payload["reasoning"] == {"effort": "minimal"}
    assert "text" in payload
    text = payload["text"]
    assert "verbosity" in text
    assert text["verbosity"] == "low"
    assert payload["input"][0]["type"] == "message"
    content = cast(ResponsesInputText, payload["input"][0]["content"][0])
    assert content["text"] == "hi"
    assert content["type"] == "input_text"
    assert "temperature" not in payload


@pytest.mark.unit
def test_build_responses_payload_maps_assistant_messages_as_output_text() -> None:
    payload = build_responses_payload(
        model="gpt-5-mini",
        messages=[
            {"role": "assistant", "content": "previous"},
            {"role": "user", "content": "hi"},
        ],
        instructions="sys",
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="minimal",
        text_verbosity="low",
        stream=False,
    )

    assert payload["input"][0]["role"] == "assistant"
    assistant_content = cast(ResponsesOutputText, payload["input"][0]["content"][0])
    assert assistant_content["type"] == "output_text"
    assert assistant_content["text"] == "previous"
    assert payload["input"][1]["role"] == "user"
    user_content = cast(ResponsesInputText, payload["input"][1]["content"][0])
    assert user_content["type"] == "input_text"
    assert user_content["text"] == "hi"


@pytest.mark.unit
def test_build_responses_payload_uses_temperature_for_non_gpt5() -> None:
    payload = build_responses_payload(
        model="Devstral-Small-2-24B",
        messages=[{"role": "user", "content": "hi"}],
        instructions=None,
        max_tokens=256,
        temperature=0.7,
        reasoning_effort=None,
        text_verbosity="high",
        stream=False,
    )

    assert payload["temperature"] == 0.7
    assert "reasoning" not in payload
    assert "text" not in payload


@pytest.mark.unit
def test_build_responses_payload_merges_text_format_and_verbosity() -> None:
    payload = build_responses_payload(
        model="gpt-5.2",
        messages=[{"role": "user", "content": "hi"}],
        instructions="sys",
        max_tokens=64,
        temperature=0.2,
        reasoning_effort="low",
        text_verbosity="high",
        stream=False,
        text_format={
            "type": "json_schema",
            "name": "test",
            "schema": {},
        },
    )

    assert "text" in payload
    text = payload["text"]
    assert "verbosity" in text
    assert text["verbosity"] == "high"
    assert "format" in text
    assert text["format"]["type"] == "json_schema"
    assert text["format"]["name"] == "test"
    assert text["format"]["schema"] == {}


@pytest.mark.unit
def test_build_responses_payload_rejects_chat_response_format_shape() -> None:
    with pytest.raises(ValueError):
        build_responses_payload(
            model="gpt-5.2",
            messages=[{"role": "user", "content": "hi"}],
            instructions="sys",
            max_tokens=64,
            temperature=0.2,
            reasoning_effort="low",
            text_verbosity="high",
            stream=False,
            text_format=cast(
                ResponsesTextFormat,
                {
                    "type": "json_schema",
                    "json_schema": {"name": "test", "schema": {}},
                },
            ),
        )


@pytest.mark.unit
def test_build_responses_payload_omits_stop_for_gpt5_nano() -> None:
    payload = build_responses_payload(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": "hi"}],
        instructions="sys",
        max_tokens=64,
        temperature=0.2,
        reasoning_effort="minimal",
        text_verbosity="low",
        stream=False,
        stop=["\n```"],
    )

    assert "stop" not in payload


@pytest.mark.unit
def test_build_responses_payload_omits_prompt_cache_retention_for_gpt5_nano() -> None:
    payload = build_responses_payload(
        model="gpt-5-nano",
        messages=[{"role": "user", "content": "hi"}],
        instructions="sys",
        max_tokens=64,
        temperature=0.2,
        reasoning_effort="minimal",
        text_verbosity="low",
        stream=False,
        prompt_cache_retention="24h",
        prompt_cache_key="key",
        allow_prompt_cache_params=True,
    )

    assert "prompt_cache_retention" not in payload
    assert "prompt_cache_key" not in payload
