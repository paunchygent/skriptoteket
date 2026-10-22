"""Responses API request bodies for the script-editor providers.

Purpose:
    Build the OpenAI Responses body the editor providers send through the LLM
    provider door. Neither editor model (GPT-6 Luna, Sol 6.1) accepts
    temperature, and the door owns prompt caching, so the body carries neither.
"""

from __future__ import annotations

from typing import Literal

from pydantic import JsonValue

from skriptoteket.infrastructure.llm.openai.types import ResponsesTextFormat

_RESPONSES_TEXT_FORMAT_ERROR = "Invalid structured output format for Responses API (text.format)."


def _validate_responses_text_format(
    text_format: ResponsesTextFormat,
) -> dict[str, JsonValue]:
    """Validate text.format for /v1/responses.

    Canonical docs:
    - Responses API: https://platform.openai.com/docs/api-reference/responses
    - Local runbook: docs/runbooks/runbook-openai-responses-api.md

    `/v1/responses` requires the `text.format` shape (not the Chat Completions
    `response_format` shape):
      {"type":"json_schema","name":"...","schema":{...}}
    """

    format_type = text_format.get("type")
    if format_type == "json_object":
        return {"type": "json_object"}
    if format_type != "json_schema":
        raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)

    name = text_format.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)
    schema = text_format.get("schema")
    if not isinstance(schema, dict):
        raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)
    out_format: dict[str, JsonValue] = {
        "type": "json_schema",
        "name": name,
        "schema": schema,
    }
    strict = text_format.get("strict")
    if isinstance(strict, bool):
        out_format["strict"] = strict
    description = text_format.get("description")
    if isinstance(description, str) and description:
        out_format["description"] = description
    return out_format


def build_responses_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    instructions: str | None,
    max_tokens: int,
    reasoning_effort: str | None,
    text_verbosity: str | None,
    stream: bool,
    store: bool | None = None,
    truncation: Literal["auto", "disabled"] | None = None,
    text_format: ResponsesTextFormat | None = None,
) -> dict[str, JsonValue]:
    input_items: list[JsonValue] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        content_type = "output_text" if role == "assistant" else "input_text"
        input_items.append(
            {
                "type": "message",
                "role": role,
                "content": [{"type": content_type, "text": content}],
            }
        )

    payload: dict[str, JsonValue] = {
        "model": model,
        "input": input_items,
        "stream": stream,
        "max_output_tokens": max_tokens,
    }
    if instructions:
        payload["instructions"] = instructions
    if store is not None:
        payload["store"] = store
    if truncation:
        payload["truncation"] = truncation
    if reasoning_effort:
        payload["reasoning"] = {"effort": reasoning_effort}

    text_config: dict[str, JsonValue] = {}
    if text_verbosity:
        text_config["verbosity"] = text_verbosity
    if text_format:
        text_config["format"] = _validate_responses_text_format(text_format)
    if text_config:
        payload["text"] = text_config

    return payload
