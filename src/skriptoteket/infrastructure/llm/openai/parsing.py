from __future__ import annotations

from collections.abc import Mapping


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


def extract_response_stream_delta(
    payload: Mapping[str, object],
    *,
    event_type: str | None = None,
) -> tuple[str, bool]:
    event = payload.get("type")
    if not isinstance(event, str):
        event = event_type or ""

    if event == "response.output_text.delta":
        delta = payload.get("delta")
        if isinstance(delta, str):
            return delta, False

    if event in {"response.completed", "response.incomplete", "response.failed"}:
        return "", True

    return "", False
