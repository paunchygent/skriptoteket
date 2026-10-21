"""Door-boundary tests for the structured answer-key provider.

Purpose:
    Prove the structured provider sends its unchanged Responses body through
    the door client with the action's caller, and maps every door outcome to
    the existing failure codes. Door limit refusals propagate untouched.

Relationships:
    Exercises ``infrastructure.llm.openai.answer_key_structured_provider``
    against ``tests.unit.llm_door_fakes.RecordingDoor``.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    StructuredLLMRequest,
    StructuredOutputSpec,
)
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
    build_answer_key_responses_payload,
)
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorReply,
    DoorRequestFailed,
    DoorTimeout,
)
from tests.unit.llm_door_fakes import (
    DoorSent,
    RecordingDoor,
    fixture_caller,
    json_reply,
    replies_in_order,
)

pytestmark = pytest.mark.unit

_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openai-gpt-5.6-luna",
        model="gpt-5.6-luna",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
        reasoning_effort=StructuredLLMReasoningEffort.LOW,
    )


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id=str(uuid4()),
        item_id="item_001",
        item_type="choice",
        prompt_template_version="v1",
        system_prompt="Answer the question.",
        user_payload='{"question": "1+1?"}',
        output_spec=StructuredOutputSpec("answer", "1", _SCHEMA),
        estimated_input_tokens=10,
        max_output_tokens=100,
    )


def _responses_body(content: dict[str, JsonValue]) -> dict[str, JsonValue]:
    return {"status": "completed", "output_text": json.dumps(content)}


async def test_sends_unchanged_responses_body_through_the_door_with_the_caller() -> None:
    request = _request()
    profile = _profile()
    caller = fixture_caller()
    door = RecordingDoor(replies_in_order([_responses_body({"answer": "2"})]))

    provider = OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5.0)
    response = await provider.complete_structured(request=request, profile=profile, caller=caller)

    assert response.content == {"answer": "2"}
    assert len(door.sent) == 1
    sent = door.sent[0]
    assert sent.operation is DoorOperation.RESPONSES
    assert sent.caller is caller
    assert sent.allow_paid_overage is False
    assert sent.timeout_seconds == 5.0
    assert sent.payload == build_answer_key_responses_payload(profile=profile, request=request)


async def test_door_timeout_maps_to_provider_timeout() -> None:
    def respond(sent: DoorSent) -> DoorReply:
        raise DoorTimeout("timed out")

    provider = OpenAIAnswerKeyStructuredProvider(door=RecordingDoor(respond), timeout_seconds=5.0)
    with pytest.raises(StructuredLLMProviderError) as caught:
        await provider.complete_structured(
            request=_request(), profile=_profile(), caller=fixture_caller()
        )
    assert caught.value.failure_code is StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT


async def test_door_request_failure_maps_to_provider_request_failed() -> None:
    def respond(sent: DoorSent) -> DoorReply:
        raise DoorRequestFailed("no answer")

    provider = OpenAIAnswerKeyStructuredProvider(door=RecordingDoor(respond), timeout_seconds=5.0)
    with pytest.raises(StructuredLLMProviderError) as caught:
        await provider.complete_structured(
            request=_request(), profile=_profile(), caller=fixture_caller()
        )
    assert caught.value.failure_code is StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED


async def test_non_2xx_door_reply_maps_to_provider_http_error_with_status() -> None:
    door = RecordingDoor(lambda sent: json_reply({"error": "busy"}, status_code=503))
    provider = OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5.0)
    with pytest.raises(StructuredLLMProviderError) as caught:
        await provider.complete_structured(
            request=_request(), profile=_profile(), caller=fixture_caller()
        )
    assert caught.value.failure_code is StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR
    assert caught.value.status_code == 503


async def test_undecodable_door_body_maps_to_provider_invalid_json() -> None:
    door = RecordingDoor(lambda sent: DoorReply(status_code=200, headers={}, body=b"not json"))
    provider = OpenAIAnswerKeyStructuredProvider(door=door, timeout_seconds=5.0)
    with pytest.raises(StructuredLLMProviderError) as caught:
        await provider.complete_structured(
            request=_request(), profile=_profile(), caller=fixture_caller()
        )
    assert caught.value.failure_code is StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON


async def test_door_limit_refusal_propagates() -> None:
    def respond(sent: DoorSent) -> DoorReply:
        raise AiDailyLimitReached(limit=AiDailyLimit.POOL)

    provider = OpenAIAnswerKeyStructuredProvider(door=RecordingDoor(respond), timeout_seconds=5.0)
    with pytest.raises(AiDailyLimitReached):
        await provider.complete_structured(
            request=_request(), profile=_profile(), caller=fixture_caller()
        )
