from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class JsonSchemaResponseFormat(TypedDict):
    type: Literal["json_schema"]
    json_schema: dict[str, object]


class ResponsesInputText(TypedDict):
    type: Literal["input_text"]
    text: str


class ResponsesInputMessage(TypedDict):
    type: Literal["message"]
    role: str
    content: list[ResponsesInputText]


class ResponsesReasoning(TypedDict):
    effort: str


class ResponsesTextConfig(TypedDict):
    verbosity: NotRequired[str]
    format: NotRequired[JsonSchemaResponseFormat]


class ResponsesPayload(TypedDict):
    model: str
    input: list[ResponsesInputMessage]
    stream: bool
    max_output_tokens: int

    instructions: NotRequired[str]
    reasoning: NotRequired[ResponsesReasoning]
    text: NotRequired[ResponsesTextConfig]
    temperature: NotRequired[float]
    store: NotRequired[bool]
    truncation: NotRequired[Literal["auto", "disabled"]]
    stop: NotRequired[list[str]]
    prompt_cache_retention: NotRequired[str]
    prompt_cache_key: NotRequired[str]
