"""Responses API structured-output formats used by the editor providers."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

from pydantic import JsonValue


class ResponsesJsonSchemaTextFormat(TypedDict):
    """Responses API structured output format (`text.format`).

    Canonical docs:
    - Responses API: https://platform.openai.com/docs/api-reference/responses

    NOTE: This is the Responses shape, not the Chat Completions `response_format`:
      {"type":"json_schema","name":"...","schema":{...}}
    """

    type: Literal["json_schema"]
    name: str
    schema: dict[str, JsonValue]
    description: NotRequired[str]
    strict: NotRequired[bool]


class ResponsesJsonObjectTextFormat(TypedDict):
    type: Literal["json_object"]


ResponsesTextFormat = ResponsesJsonSchemaTextFormat | ResponsesJsonObjectTextFormat
