from __future__ import annotations

from typing import Literal

from skriptoteket.infrastructure.llm.model_families import (
    is_gpt5_family_model,
    supports_prompt_cache_key,
    supports_prompt_cache_retention,
    supports_stop_sequences,
)
from skriptoteket.infrastructure.llm.openai.types import (
    JsonSchemaResponseFormat,
    ResponsesInputMessage,
    ResponsesJsonSchemaTextFormat,
    ResponsesMessageContent,
    ResponsesPayload,
    ResponsesTextConfig,
    ResponsesTextFormat,
)

_RESPONSES_TEXT_FORMAT_ERROR = "Invalid structured output format for Responses API (text.format)."


def _normalize_responses_text_format(
    text_format: JsonSchemaResponseFormat | ResponsesTextFormat,
) -> ResponsesTextFormat:
    """Normalize text.format for /v1/responses.

    Canonical docs:
    - Responses API: https://platform.openai.com/docs/api-reference/responses
    - Chat Completions API: https://platform.openai.com/docs/api-reference/chat
    - Local runbook: docs/runbooks/runbook-openai-responses-api.md

    OpenAI Chat Completions uses (response_format):
      {"type":"json_schema","json_schema":{"name":"...","schema":{...}}}

    Responses uses (text.format):
      {"type":"json_schema","name":"...","schema":{...}}
    """

    format_type = text_format.get("type")
    if format_type == "json_object":
        return {"type": "json_object"}
    if format_type != "json_schema":
        raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)

    if "json_schema" in text_format:
        nested = text_format.get("json_schema")
        if not isinstance(nested, dict):
            raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)
        name = nested.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)
        schema = nested.get("schema")
        if not isinstance(schema, dict):
            raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)

        out_format_nested: ResponsesJsonSchemaTextFormat = {
            "type": "json_schema",
            "name": name,
            "schema": schema,
        }
        strict = nested.get("strict")
        if isinstance(strict, bool):
            out_format_nested["strict"] = strict
        description = nested.get("description")
        if isinstance(description, str) and description:
            out_format_nested["description"] = description
        return out_format_nested

    name = text_format.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)
    schema = text_format.get("schema")
    if not isinstance(schema, dict):
        raise ValueError(_RESPONSES_TEXT_FORMAT_ERROR)
    out_format: ResponsesJsonSchemaTextFormat = {
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


def build_chat_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    reasoning_effort: str | None,
    stream: bool,
    stop: list[str] | None = None,
    cache_prompt: bool = False,
    prompt_cache_retention: str | None = None,
    prompt_cache_key: str | None = None,
    allow_prompt_cache_params: bool = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }

    if is_gpt5_family_model(model=model):
        payload["max_completion_tokens"] = max_tokens
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
    else:
        payload["max_tokens"] = max_tokens
        payload["temperature"] = temperature

    if stop and supports_stop_sequences(model=model):
        payload["stop"] = stop
    if cache_prompt:
        payload["cache_prompt"] = True
    if allow_prompt_cache_params:
        if prompt_cache_retention and supports_prompt_cache_retention(model=model):
            payload["prompt_cache_retention"] = prompt_cache_retention
        if prompt_cache_key and supports_prompt_cache_key(model=model):
            payload["prompt_cache_key"] = prompt_cache_key

    return payload


def build_responses_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    instructions: str | None,
    max_tokens: int,
    temperature: float,
    reasoning_effort: str | None,
    text_verbosity: str | None,
    stream: bool,
    store: bool | None = None,
    truncation: Literal["auto", "disabled"] | None = None,
    stop: list[str] | None = None,
    prompt_cache_retention: str | None = None,
    prompt_cache_key: str | None = None,
    allow_prompt_cache_params: bool = True,
    text_format: JsonSchemaResponseFormat | ResponsesTextFormat | None = None,
) -> ResponsesPayload:
    input_items: list[ResponsesInputMessage] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        if role == "assistant":
            content_item: ResponsesMessageContent = {"type": "output_text", "text": content}
        else:
            content_item = {"type": "input_text", "text": content}
        input_items.append(
            {
                "type": "message",
                "role": role,
                "content": [content_item],
            }
        )

    payload: ResponsesPayload = {
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

    text_config: ResponsesTextConfig = {}
    if is_gpt5_family_model(model=model):
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}
        if text_verbosity:
            text_config["verbosity"] = text_verbosity
    else:
        payload["temperature"] = temperature

    if text_format:
        text_config["format"] = _normalize_responses_text_format(text_format)
    if text_config:
        payload["text"] = text_config

    if stop and supports_stop_sequences(model=model):
        payload["stop"] = stop

    if allow_prompt_cache_params:
        if prompt_cache_retention and supports_prompt_cache_retention(model=model):
            payload["prompt_cache_retention"] = prompt_cache_retention
        if prompt_cache_key and supports_prompt_cache_key(model=model):
            payload["prompt_cache_key"] = prompt_cache_key

    return payload
