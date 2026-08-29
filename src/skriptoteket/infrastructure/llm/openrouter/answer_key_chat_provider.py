"""httpx OpenRouter Chat Completions adapter for structured answer keys.

Purpose:
    Execute item-local structured answer-key requests against the OpenRouter
    Chat Completions endpoint with strict JSON Schema output, ported from
    sir-convert-a-lot `76983339` and trimmed to the failover-only GLM lane.

Relationships:
    Implements ``protocols.exam_answer_key.AnswerKeyStructuredProviderProtocol``
    for ``StructuredLLMEndpointKind.CHAT_COMPLETIONS`` profiles. Payload facts
    (POST {base}/chat/completions, Bearer auth, ``response_format.json_schema``,
    ``provider.require_parameters``) are pinned against current OpenRouter docs
    at implementation time.
"""

from __future__ import annotations

import json

import httpx
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.protocols.exam_answer_key import AnswerKeyStructuredProviderProtocol

_JsonObject = dict[str, JsonValue]


class OpenRouterAnswerKeyChatProvider(AnswerKeyStructuredProviderProtocol):
    """Async OpenRouter Chat Completions adapter for structured requests."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
    ) -> None:
        if not base_url.strip():
            raise ValueError("Answer-key failover base_url must be non-empty.")
        if timeout_seconds <= 0:
            raise ValueError("Answer-key failover timeout_seconds must be positive.")
        self._client = client
        self._base_url = base_url.strip().rstrip("/")
        self._api_key = api_key.strip()
        self._timeout_seconds = timeout_seconds

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        if profile.endpoint_kind is not StructuredLLMEndpointKind.CHAT_COMPLETIONS:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_CONFIG_MISSING,
                message="Only the Chat Completions endpoint is configured in this lane.",
                provider_id=profile.provider_id,
            )
        if not self._api_key:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_CONFIG_MISSING,
                message="Answer-key failover provider API key is not configured.",
                provider_id=profile.provider_id,
            )
        payload = build_answer_key_chat_completions_payload(profile=profile, request=request)
        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
                message="Structured provider returned an unsuccessful HTTP status.",
                provider_id=profile.provider_id,
                status_code=exc.response.status_code,
            ) from exc
        except httpx.TimeoutException as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
                message="Structured provider request timed out.",
                provider_id=profile.provider_id,
            ) from exc
        except httpx.RequestError as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED,
                message="Structured provider request failed before a response was received.",
                provider_id=profile.provider_id,
            ) from exc

        try:
            body: JsonValue = response.json()
        except ValueError as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON,
                message="Structured provider response body was not valid JSON.",
                provider_id=profile.provider_id,
            ) from exc
        return parse_answer_key_chat_completions_payload(payload=body, profile=profile)


def build_answer_key_chat_completions_payload(
    *,
    profile: StructuredLLMProviderProfile,
    request: StructuredLLMRequest,
) -> _JsonObject:
    """Build the Chat Completions payload with strict JSON Schema output."""

    return {
        "model": profile.model,
        "messages": [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_payload},
        ],
        "stream": False,
        "max_tokens": request.max_output_tokens,
        "temperature": profile.temperature,
        "provider": {"require_parameters": True},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": request.output_spec.schema_name,
                "strict": request.output_spec.strict,
                "schema": request.output_spec.json_schema,
            },
        },
    }


def parse_answer_key_chat_completions_payload(
    *,
    payload: JsonValue,
    profile: StructuredLLMProviderProfile,
) -> StructuredLLMResponse:
    """Parse one Chat Completions payload into a validated structured response."""

    if not isinstance(payload, dict):
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
            message="Structured provider response was not a JSON object.",
        )
    message, finish_reason = _extract_choice(payload=payload, profile=profile)
    if isinstance(message.get("refusal"), str):
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_REFUSAL,
            message="Structured provider returned a refusal instead of schema content.",
        )
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_EMPTY_CONTENT,
            message="Structured provider response did not contain model content.",
        )
    return StructuredLLMResponse(
        content=_loads_content_object(content=content, profile=profile),
        finish_reason=finish_reason,
        usage=_extract_usage(payload),
    )


def _extract_choice(
    *,
    payload: _JsonObject,
    profile: StructuredLLMProviderProfile,
) -> tuple[_JsonObject, str | None]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_EMPTY_CONTENT,
            message="Structured provider response did not contain choices.",
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
            message="Structured provider choice was not a JSON object.",
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
            message="Structured provider choice message was not a JSON object.",
        )
    finish_reason = choice.get("finish_reason")
    return message, finish_reason if isinstance(finish_reason, str) else None


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
        prompt_tokens=_optional_int(usage.get("prompt_tokens")),
        completion_tokens=_optional_int(usage.get("completion_tokens")),
        total_tokens=_optional_int(usage.get("total_tokens")),
    )


def _optional_int(value: JsonValue | None) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


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
