"""Payload and parsing rules for the OpenRouter answer-key chat adapter.

Purpose:
    Pin the Chat Completions request shape (Bearer-authenticated POST body
    with strict ``response_format.json_schema`` and
    ``provider.require_parameters``) and the response parsing rules for the
    GLM failover lane against current OpenRouter docs.
"""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredOutputSpec,
)
from skriptoteket.infrastructure.llm.openrouter.answer_key_chat_provider import (
    OpenRouterAnswerKeyChatProvider,
    build_answer_key_chat_completions_payload,
    parse_answer_key_chat_completions_payload,
)

pytestmark = pytest.mark.unit


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openrouter-glm-5.3-flash",
        model="z-ai/glm-5.3-flash",
        endpoint_kind=StructuredLLMEndpointKind.CHAT_COMPLETIONS,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
    )


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="job-1",
        item_id="item-1",
        item_type="single_choice",
        prompt_template_version="v1",
        system_prompt="You pick the correct alternative.",
        user_payload='{"alternatives": [1, 2]}',
        output_spec=StructuredOutputSpec(
            schema_name="choice_decision",
            schema_version="v1",
            json_schema={
                "type": "object",
                "properties": {"correct_alternative_ids": {"type": "array"}},
                "required": ["correct_alternative_ids"],
                "additionalProperties": False,
            },
        ),
        estimated_input_tokens=100,
        max_output_tokens=512,
    )


def test_payload_pins_the_openrouter_chat_completions_shape() -> None:
    payload = build_answer_key_chat_completions_payload(
        profile=_profile(), request=_request(), temperature=0.0
    )

    assert payload["model"] == "z-ai/glm-5.3-flash"
    assert payload["messages"] == [
        {"role": "system", "content": "You pick the correct alternative."},
        {"role": "user", "content": '{"alternatives": [1, 2]}'},
    ]
    assert payload["stream"] is False
    assert payload["max_tokens"] == 512
    assert payload["temperature"] == 0.0
    assert payload["provider"] == {"require_parameters": True}
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "choice_decision",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"correct_alternative_ids": {"type": "array"}},
                "required": ["correct_alternative_ids"],
                "additionalProperties": False,
            },
        },
    }


def test_parse_reads_content_finish_reason_and_usage() -> None:
    payload: JsonValue = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": '{"correct_alternative_ids": [2]}'},
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
    }

    response = parse_answer_key_chat_completions_payload(payload=payload, profile=_profile())

    assert response.content == {"correct_alternative_ids": [2]}
    assert response.finish_reason == "stop"
    assert response.usage.usable_total_tokens == 150


def test_parse_maps_refusal_to_the_refusal_failure_code() -> None:
    payload: JsonValue = {
        "choices": [{"message": {"role": "assistant", "refusal": "cannot comply"}}],
    }

    with pytest.raises(StructuredLLMProviderError) as excinfo:
        parse_answer_key_chat_completions_payload(payload=payload, profile=_profile())
    assert excinfo.value.failure_code is StructuredLLMBackendFailureCode.PROVIDER_REFUSAL


@pytest.mark.parametrize(
    ("payload", "failure_code"),
    [
        ([], StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT),
        ({"choices": []}, StructuredLLMBackendFailureCode.PROVIDER_EMPTY_CONTENT),
        (
            {"choices": [{"message": {"role": "assistant", "content": ""}}]},
            StructuredLLMBackendFailureCode.PROVIDER_EMPTY_CONTENT,
        ),
        (
            {"choices": [{"message": {"role": "assistant", "content": "not json"}}]},
            StructuredLLMBackendFailureCode.PROVIDER_CONTENT_NOT_JSON,
        ),
        (
            {"choices": [{"message": {"role": "assistant", "content": "[1, 2]"}}]},
            StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
        ),
    ],
)
def test_parse_maps_malformed_payloads_to_typed_failures(
    payload: JsonValue,
    failure_code: StructuredLLMBackendFailureCode,
) -> None:
    with pytest.raises(StructuredLLMProviderError) as excinfo:
        parse_answer_key_chat_completions_payload(payload=payload, profile=_profile())
    assert excinfo.value.failure_code is failure_code


# The request body before temperature moved from the shared profile onto this provider
# (TASK-SKRIPT-39-04-11 D4), serialized compactly; the move must not change one byte.
_PINNED_BODY = (
    '{"model":"z-ai/glm-5.3-flash","messages":[{"role":"system","content":"You pick t'
    'he correct alternative."},{"role":"user","content":"{\\"alternatives\\": [1, 2]}"}'
    '],"stream":false,"max_tokens":512,"temperature":0.0,"provider":{"require_paramet'
    'ers":true},"response_format":{"type":"json_schema","json_schema":{"name":"choice'
    '_decision","strict":true,"schema":{"type":"object","properties":{"correct_altern'
    'ative_ids":{"type":"array"}},"required":["correct_alternative_ids"],"additionalP'
    'roperties":false}}}}'
)


def test_payload_bytes_are_pinned() -> None:
    payload = build_answer_key_chat_completions_payload(
        profile=_profile(), request=_request(), temperature=0.0
    )

    assert json.dumps(payload, separators=(",", ":"), ensure_ascii=False) == _PINNED_BODY


async def test_the_provider_posts_its_own_temperature_in_the_pinned_body() -> None:
    posted: list[bytes] = []

    def handle(request: httpx.Request) -> httpx.Response:
        posted.append(request.content)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = OpenRouterAnswerKeyChatProvider(
            client=client,
            base_url="https://openrouter.test/api/v1",
            api_key="key",
            timeout_seconds=5.0,
            temperature=0.0,
        )
        with pytest.raises(StructuredLLMProviderError):
            await provider.complete_structured(request=_request(), profile=_profile())

    (body,) = posted
    assert json.loads(body) == json.loads(_PINNED_BODY)
    assert body == _PINNED_BODY.encode()


@pytest.mark.parametrize("temperature", [-0.1, 2.1])
def test_the_provider_rejects_a_temperature_outside_zero_to_two(temperature: float) -> None:
    with pytest.raises(ValueError, match="temperature"):
        OpenRouterAnswerKeyChatProvider(
            client=httpx.AsyncClient(),
            base_url="https://openrouter.test/api/v1",
            api_key="key",
            timeout_seconds=5.0,
            temperature=temperature,
        )


def test_the_shared_profile_has_no_temperature() -> None:
    assert not hasattr(_profile(), "temperature")


async def test_the_provider_posts_the_temperature_it_was_configured_with() -> None:
    posted: list[bytes] = []

    def handle(request: httpx.Request) -> httpx.Response:
        posted.append(request.content)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        provider = OpenRouterAnswerKeyChatProvider(
            client=client,
            base_url="https://openrouter.test/api/v1",
            api_key="key",
            timeout_seconds=5.0,
            temperature=0.7,
        )
        with pytest.raises(StructuredLLMProviderError):
            await provider.complete_structured(request=_request(), profile=_profile())

    (body,) = posted
    assert json.loads(body)["temperature"] == 0.7
