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
