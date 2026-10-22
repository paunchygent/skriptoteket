"""Door answers to editor AI failures.

Purpose:
    Map what the LLM provider door returns for an editor Responses call to
    ``EditorLlmProviderError`` (kinds in ``protocols.llm.common``), so the
    three editor providers fail the same way. A daily-limit refusal and a busy
    door are not mapped: ``AiDailyLimitReached`` and ``AiDoorBusy`` propagate
    untouched.

Relationships:
    Used by the inline completion, chat ops and chat stream providers.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final

from pydantic import JsonValue

from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.llm.common import EditorLlmProviderError
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorRequestFailed,
    DoorTimeout,
    LlmDoorClientProtocol,
)

_DETAIL_MAX_CHARS: Final = 2000
_CONTEXT_LENGTH_EXCEEDED_CODE: Final = "context_length_exceeded"


def _detail(body: bytes) -> str:
    return body.decode("utf-8", errors="replace")[:_DETAIL_MAX_CHARS]


def _is_context_length_exceeded(body: bytes) -> bool:
    try:
        decoded: JsonValue = json.loads(body)
    except ValueError:
        return False
    if not isinstance(decoded, dict):
        return False
    error = decoded.get("error")
    return isinstance(error, dict) and error.get("code") == _CONTEXT_LENGTH_EXCEEDED_CODE


def failure_for_status(*, status_code: int, body: bytes) -> EditorLlmProviderError:
    """The error for an unsuccessful relayed answer or stream."""

    if _is_context_length_exceeded(body):
        return EditorLlmProviderError(
            kind="context_window_exceeded",
            status_code=status_code,
            detail=_detail(body),
        )
    return EditorLlmProviderError(
        kind="http_status",
        status_code=status_code,
        detail=_detail(body),
    )


def invalid_response(*, detail: str) -> EditorLlmProviderError:
    """The error for an answer or stream event that cannot be parsed."""

    return EditorLlmProviderError(kind="invalid_response", detail=detail[:_DETAIL_MAX_CHARS])


async def send_responses_call(
    *,
    door: LlmDoorClientProtocol,
    payload: Mapping[str, JsonValue],
    caller: AiDoorCaller,
    timeout_seconds: float,
) -> dict[str, JsonValue]:
    """Send one non-streamed Responses call and return its parsed JSON object."""

    try:
        reply = await door.send(
            operation=DoorOperation.RESPONSES,
            payload=payload,
            caller=caller,
            timeout_seconds=timeout_seconds,
        )
    except DoorTimeout as exc:
        raise EditorLlmProviderError(kind="timeout") from exc
    except DoorRequestFailed as exc:
        raise EditorLlmProviderError(kind="request_failed") from exc
    if not reply.is_success:
        raise failure_for_status(status_code=reply.status_code, body=reply.body)
    try:
        decoded: JsonValue = json.loads(reply.body)
    except ValueError as exc:
        raise invalid_response(detail=_detail(reply.body)) from exc
    if not isinstance(decoded, dict):
        raise invalid_response(detail=_detail(reply.body))
    return decoded
