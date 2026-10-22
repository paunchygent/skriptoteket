from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final

_TERMINAL_EVENTS: Final = frozenset(
    {"response.completed", "response.incomplete", "response.failed"}
)


def _extract_response_finish_reason(payload: Mapping[str, object]) -> str | None:
    status = payload.get("status")
    if not isinstance(status, str):
        return None
    if status == "completed":
        return "stop"
    if status == "incomplete":
        details = payload.get("incomplete_details")
        if isinstance(details, Mapping):
            reason = details.get("reason")
            if isinstance(reason, str):
                if reason == "max_output_tokens":
                    return "length"
                return reason
        return "incomplete"
    return status


def extract_response_output_text(payload: Mapping[str, object]) -> tuple[str, str | None]:
    finish_reason = _extract_response_finish_reason(payload)

    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text, finish_reason

    output_items = payload.get("output")
    if not isinstance(output_items, list):
        raise ValueError("Upstream LLM response is missing output")

    text_parts: list[str] = []
    for item in output_items:
        if not isinstance(item, Mapping):
            continue
        item_type = item.get("type")
        if item_type == "message":
            content = item.get("content")
            if isinstance(content, str):
                text_parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if not isinstance(part, Mapping):
                        continue
                    if part.get("type") != "output_text":
                        continue
                    text = part.get("text")
                    if isinstance(text, str):
                        text_parts.append(text)
        elif item_type == "output_text":
            text = item.get("text")
            if isinstance(text, str):
                text_parts.append(text)

    return "".join(text_parts), finish_reason


def _terminal_failure(event: str, payload: Mapping[str, object]) -> str | None:
    """Why a terminal event is not a successful completion, or ``None`` for one."""

    response = payload.get("response")
    if event == "response.completed":
        if not isinstance(response, Mapping):
            return None
        status = response.get("status")
        if isinstance(status, str) and status != "completed":
            return f"response.completed carried a response with status {status}"
        return None

    if event == "response.incomplete":
        reason = "unknown"
        if isinstance(response, Mapping):
            details = response.get("incomplete_details")
            if isinstance(details, Mapping) and isinstance(details.get("reason"), str):
                reason = str(details["reason"])
        return f"response.incomplete: {reason}"

    error = response.get("error") if isinstance(response, Mapping) else None
    if error is None:
        return f"response.failed: {json.dumps(payload, default=str)}"
    return f"response.failed: {json.dumps(error, default=str)}"


def extract_response_stream_delta(
    payload: Mapping[str, object],
    *,
    event_type: str | None = None,
) -> tuple[str, bool]:
    """Read one Responses stream event as ``(text delta, completed)``.

    Only ``response.completed`` is the successful end of a stream. A stream
    ``error`` event, ``response.failed``, ``response.incomplete``, a
    ``response.completed`` whose response did not complete and a delta that is
    not text raise ``ValueError`` with a message for the failure detail.
    """

    event = payload.get("type")
    if not isinstance(event, str):
        event = event_type or ""

    if event == "error" or "error" in payload:
        raise ValueError(f"stream error event: {json.dumps(payload, default=str)}")

    if event == "response.output_text.delta":
        delta = payload.get("delta")
        if not isinstance(delta, str):
            raise ValueError(f"stream delta is not text: {json.dumps(payload, default=str)}")
        return delta, False

    if event in _TERMINAL_EVENTS:
        failure = _terminal_failure(event, payload)
        if failure is not None:
            raise ValueError(failure)
        return "", True

    return "", False
