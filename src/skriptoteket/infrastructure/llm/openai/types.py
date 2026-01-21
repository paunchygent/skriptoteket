from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class ChatCompletionsJsonSchemaResponseFormat(TypedDict):
    """Chat Completions structured output format (`response_format`).

    Canonical docs:
    - Chat Completions API: https://platform.openai.com/docs/api-reference/chat

    NOTE: The Responses API uses a different shape under `text.format`.
    See `ResponsesTextFormat` below.
    """

    type: Literal["json_schema"]
    json_schema: dict[str, object]


class ResponsesJsonSchemaTextFormat(TypedDict):
    """Responses API structured output format (`text.format`).

    Canonical docs:
    - Responses API: https://platform.openai.com/docs/api-reference/responses

    NOTE: This is intentionally *not* the same as Chat Completions `response_format`:
      - Chat:     {"type":"json_schema","json_schema":{"name":"...","schema":{...}}}
      - Responses:{"type":"json_schema","name":"...","schema":{...}}
    """

    type: Literal["json_schema"]
    name: str
    schema: dict[str, object]
    description: NotRequired[str]
    strict: NotRequired[bool]


class ResponsesJsonObjectTextFormat(TypedDict):
    type: Literal["json_object"]


ResponsesTextFormat = ResponsesJsonSchemaTextFormat | ResponsesJsonObjectTextFormat


class ResponsesInputText(TypedDict):
    type: Literal["input_text"]
    text: str


class ResponsesOutputText(TypedDict):
    type: Literal["output_text"]
    text: str


class ResponsesRefusal(TypedDict):
    type: Literal["refusal"]
    refusal: str


ResponsesMessageContent = ResponsesInputText | ResponsesOutputText | ResponsesRefusal


class ResponsesInputMessage(TypedDict):
    type: Literal["message"]
    role: str
    content: list[ResponsesMessageContent]


class ResponsesReasoning(TypedDict):
    effort: str


class ResponsesTextConfig(TypedDict):
    verbosity: NotRequired[str]
    format: NotRequired[ResponsesTextFormat]


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
