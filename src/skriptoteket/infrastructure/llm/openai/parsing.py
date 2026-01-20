from __future__ import annotations

from collections.abc import Mapping


def extract_first_choice_content(payload: Mapping[str, object]) -> tuple[str, str | None]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Upstream LLM response is missing choices")

    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("Upstream LLM response choice is not an object")

    finish_reason = first.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        finish_reason = None

    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content, finish_reason

    text = first.get("text")
    if isinstance(text, str):
        return text, finish_reason

    return "", finish_reason


def extract_first_choice_delta(payload: Mapping[str, object]) -> tuple[str, str | None]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Upstream LLM stream chunk is missing choices")

    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("Upstream LLM stream chunk choice is not an object")

    finish_reason = first.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        finish_reason = None

    delta = first.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str):
            return content, finish_reason

        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") != "text":
                    continue
                text = part.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
            if text_parts:
                return "".join(text_parts), finish_reason

    text = first.get("text")
    if isinstance(text, str):
        return text, finish_reason

    return "", finish_reason


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
