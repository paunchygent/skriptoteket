"""Door-backed Responses adapter for structured answer-key completion.

Purpose:
    Execute item-local structured answer-key requests through HuleEdu's LLM
    provider door (ST-SKRIPT-41-01 B2): the Responses body is unchanged, the
    door client owns the key, the teacher's user id, the exempt flag and the
    paid-overage mode, and the relayed answer parses as before.

Relationships:
    Implements ``protocols.exam_answer_key.AnswerKeyStructuredProviderProtocol``.
    Payload facts (text.format json_schema, reasoning effort, usage fields)
    are pinned against current OpenAI docs at implementation time.
"""

from __future__ import annotations

import json

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
    input_content,
)
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.infrastructure.llm.openai.structured_stream import (
    ResponseStreamError,
    ResponseStreamRefusal,
    observe_response_stream,
)
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
    StructuredLLMTextObserver,
)
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorReply,
    DoorRequestFailed,
    DoorTimeout,
    LlmDoorClientProtocol,
)

_JsonObject = dict[str, JsonValue]


class OpenAIAnswerKeyStructuredProvider(AnswerKeyStructuredProviderProtocol):
    """Structured answer-key requests sent through the provider door."""

    def __init__(
        self,
        *,
        door: LlmDoorClientProtocol,
        timeout_seconds: float,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("Answer-key provider timeout_seconds must be positive.")
        self._door = door
        self._timeout_seconds = timeout_seconds

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        on_text: StructuredLLMTextObserver | None = None,
    ) -> StructuredLLMResponse:
        if profile.endpoint_kind is not StructuredLLMEndpointKind.RESPONSES:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_CONFIG_MISSING,
                message="Only the OpenAI Responses endpoint is configured in this lane.",
                provider_id=profile.provider_id,
            )
        payload = build_answer_key_responses_payload(profile=profile, request=request)
        try:
            if on_text is not None:
                payload["stream"] = True
                async with self._door.stream(
                    operation=DoorOperation.RESPONSES,
                    payload=payload,
                    caller=caller,
                    timeout_seconds=self._timeout_seconds,
                ) as stream:
                    if not stream.is_success:
                        return _parse_door_reply(
                            reply=DoorReply(
                                status_code=stream.status_code,
                                headers=stream.headers,
                                body=stream.body,
                            ),
                            profile=profile,
                        )
                    body = await observe_response_stream(
                        lines=stream.aiter_lines(), on_text=on_text
                    )
                return parse_answer_key_responses_payload(payload=body, profile=profile)
            reply = await self._door.send(
                operation=DoorOperation.RESPONSES,
                payload=payload,
                caller=caller,
                timeout_seconds=self._timeout_seconds,
            )
        except ResponseStreamRefusal as exc:
            raise _refusal_error(profile) from exc
        except ResponseStreamError as exc:
            raise _provider_error(
                profile=profile,
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED,
                message=str(exc),
            ) from exc
        except DoorTimeout as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
                message="Structured provider request timed out.",
                provider_id=profile.provider_id,
            ) from exc
        except DoorRequestFailed as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED,
                message="Structured provider request failed before a response was received.",
                provider_id=profile.provider_id,
            ) from exc
        return _parse_door_reply(reply=reply, profile=profile)


def _parse_door_reply(
    *,
    reply: DoorReply,
    profile: StructuredLLMProviderProfile,
) -> StructuredLLMResponse:
    if not reply.is_success:
        raise StructuredLLMProviderError(
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
            message="Structured provider returned an unsuccessful HTTP status.",
            provider_id=profile.provider_id,
            status_code=reply.status_code,
        )
    try:
        body: JsonValue = json.loads(reply.body)
    except ValueError as exc:
        raise StructuredLLMProviderError(
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON,
            message="Structured provider response body was not valid JSON.",
            provider_id=profile.provider_id,
        ) from exc
    return parse_answer_key_responses_payload(payload=body, profile=profile)


def build_answer_key_responses_payload(
    *,
    profile: StructuredLLMProviderProfile,
    request: StructuredLLMRequest,
) -> _JsonObject:
    """Build the OpenAI Responses payload with strict JSON Schema output."""

    text_config: _JsonObject = {
        "format": {
            "type": "json_schema",
            "name": request.output_spec.schema_name,
            "strict": request.output_spec.strict,
            "schema": request.output_spec.json_schema,
        }
    }
    if profile.text_verbosity is not None:
        text_config["verbosity"] = profile.text_verbosity.value
    payload: _JsonObject = {
        "model": profile.model,
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": input_content(request.user_payload, request.user_images),
            }
        ],
        "instructions": request.system_prompt,
        "stream": False,
        "max_output_tokens": request.max_output_tokens,
        "store": False,
        "text": text_config,
    }
    if profile.reasoning_effort is not None:
        payload["reasoning"] = {"effort": profile.reasoning_effort.value}
    return payload


def parse_answer_key_responses_payload(
    *,
    payload: JsonValue,
    profile: StructuredLLMProviderProfile,
) -> StructuredLLMResponse:
    """Parse one Responses payload into a validated structured response."""

    if not isinstance(payload, dict):
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
            message="Structured provider response was not a JSON object.",
        )
    content = _extract_responses_content(payload=payload, profile=profile)
    status = payload.get("status")
    return StructuredLLMResponse(
        content=content,
        finish_reason=status if isinstance(status, str) else None,
        usage=_extract_usage(payload),
    )


def _extract_responses_content(
    *,
    payload: _JsonObject,
    profile: StructuredLLMProviderProfile,
) -> _JsonObject:
    if isinstance(payload.get("refusal"), str):
        raise _refusal_error(profile)
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return _loads_content_object(content=output_text, profile=profile)
    output_items = payload.get("output")
    if isinstance(output_items, list):
        for item in output_items:
            extracted = _extract_output_item(item=item, profile=profile)
            if extracted is not None:
                return extracted
    raise _provider_error(
        profile=profile,
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_EMPTY_CONTENT,
        message="Structured provider response did not contain model content.",
    )


def _extract_output_item(
    *,
    item: JsonValue,
    profile: StructuredLLMProviderProfile,
) -> _JsonObject | None:
    if not isinstance(item, dict):
        return None
    if isinstance(item.get("refusal"), str):
        raise _refusal_error(profile)
    content_items = item.get("content")
    if not isinstance(content_items, list):
        return None
    for content_item in content_items:
        if not isinstance(content_item, dict):
            continue
        if isinstance(content_item.get("refusal"), str) or content_item.get("type") == "refusal":
            raise _refusal_error(profile)
        text = content_item.get("text")
        if isinstance(text, str) and text.strip():
            return _loads_content_object(content=text, profile=profile)
    return None


def _loads_content_object(
    *,
    content: str,
    profile: StructuredLLMProviderProfile,
) -> _JsonObject:
    try:
        decoded: JsonValue = json.loads(content)
    except json.JSONDecodeError as exc:
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_CONTENT_NOT_JSON,
            message="Structured provider content was not valid JSON.",
        ) from exc
    if not isinstance(decoded, dict):
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
            message="Structured provider content JSON was not an object.",
        )
    return decoded


def _extract_usage(payload: _JsonObject) -> StructuredLLMUsage:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return StructuredLLMUsage()
    return StructuredLLMUsage(
        prompt_tokens=_optional_int(usage.get("input_tokens")),
        completion_tokens=_optional_int(usage.get("output_tokens")),
        total_tokens=_optional_int(usage.get("total_tokens")),
    )


def _optional_int(value: JsonValue | None) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _refusal_error(profile: StructuredLLMProviderProfile) -> StructuredLLMProviderError:
    return _provider_error(
        profile=profile,
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_REFUSAL,
        message="Structured provider returned a refusal instead of schema content.",
    )


def _provider_error(
    *,
    profile: StructuredLLMProviderProfile,
    failure_code: StructuredLLMBackendFailureCode,
    message: str,
) -> StructuredLLMProviderError:
    return StructuredLLMProviderError(
        failure_code=failure_code,
        message=message,
        provider_id=profile.provider_id,
    )
