from __future__ import annotations

import json
from typing import TypeGuard

import httpx
import pytest

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.openai.chat_stream_provider import (
    OpenAIChatStreamProvider,
)
from skriptoteket.infrastructure.llm.openai.inline_completion_provider import (
    OpenAIInlineCompletionProvider,
)
from skriptoteket.infrastructure.llm.openai.types import (
    ResponsesInputMessage,
    ResponsesInputText,
    ResponsesPayload,
)
from skriptoteket.protocols.llm import ChatMessage, LLMChatRequest, LLMCompletionRequest


def _is_responses_input_text(value: object) -> TypeGuard[ResponsesInputText]:
    if not isinstance(value, dict):
        return False
    return value.get("type") == "input_text" and isinstance(value.get("text"), str)


def _is_responses_input_message(value: object) -> TypeGuard[ResponsesInputMessage]:
    if not isinstance(value, dict):
        return False
    if value.get("type") != "message":
        return False
    if not isinstance(value.get("role"), str):
        return False
    content = value.get("content")
    if not isinstance(content, list):
        return False
    return all(_is_responses_input_text(item) for item in content)


def _is_responses_payload(value: object) -> TypeGuard[ResponsesPayload]:
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("model"), str):
        return False
    if not isinstance(value.get("stream"), bool):
        return False
    if not isinstance(value.get("max_output_tokens"), int):
        return False
    input_items = value.get("input")
    if not isinstance(input_items, list):
        return False
    return all(_is_responses_input_message(item) for item in input_items)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inline_completion_uses_responses_api_for_openai() -> None:
    captured: ResponsesPayload | None = None
    captured_url: str | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured, captured_url
        decoded: object = json.loads(request.content.decode("utf-8"))
        assert _is_responses_payload(decoded)
        captured = decoded
        captured_url = str(request.url)
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "done"}],
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIInlineCompletionProvider(
            settings=Settings(),
            client=client,
            base_url="https://api.openai.com/v1",
            api_key="sk-no-key",
            model="gpt-5-nano",
        )
        response = await provider.complete_inline(
            request=LLMCompletionRequest(prefix="pre", suffix="suf"),
            system_prompt="sys",
        )

    assert response.completion == "done"
    assert captured_url is not None
    assert captured_url.endswith("/responses")
    assert captured is not None
    assert "instructions" in captured
    assert captured["instructions"] == "sys"
    prompt_text = captured["input"][0]["content"][0]["text"]
    assert "pre" in prompt_text and "suf" in prompt_text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_stream_uses_responses_api_for_openai() -> None:
    captured: ResponsesPayload | None = None
    captured_url: str | None = None

    stream_body = (
        "event: response.output_text.delta\n"
        'data: {"type":"response.output_text.delta","delta":"Hello"}\n\n'
        "event: response.completed\n"
        'data: {"type":"response.completed"}\n\n'
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured, captured_url
        decoded: object = json.loads(request.content.decode("utf-8"))
        assert _is_responses_payload(decoded)
        captured = decoded
        captured_url = str(request.url)
        return httpx.Response(200, content=stream_body.encode("utf-8"))

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIChatStreamProvider(
            settings=Settings(),
            client=client,
            base_url="https://api.openai.com/v1",
            api_key="sk-no-key",
            model="gpt-5.2",
        )
        chunks = [
            chunk
            async for chunk in provider.stream_chat(
                request=LLMChatRequest(
                    messages=[ChatMessage(role="user", content="hi")],
                ),
                system_prompt="sys",
            )
        ]

    assert chunks == ["Hello"]
    assert captured_url is not None
    assert captured_url.endswith("/responses")
    assert captured is not None
    assert "instructions" in captured
    assert captured["instructions"] == "sys"
