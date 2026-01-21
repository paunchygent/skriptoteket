from __future__ import annotations

import json
from typing import TypeGuard

import httpx
import pytest

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.openai.chat_ops_provider import OpenAIChatOpsProvider
from skriptoteket.infrastructure.llm.openai.grammars import (
    EDIT_OPS_PATCH_ONLY_GBNF,
    EDIT_OPS_PATCH_ONLY_RESPONSE_FORMAT,
)
from skriptoteket.infrastructure.llm.openai.types import (
    ResponsesInputMessage,
    ResponsesMessageContent,
    ResponsesPayload,
)
from skriptoteket.protocols.llm import ChatMessage, LLMChatRequest


def _is_responses_message_content(value: object) -> TypeGuard[ResponsesMessageContent]:
    if not isinstance(value, dict):
        return False
    content_type = value.get("type")
    if content_type in {"input_text", "output_text"}:
        return isinstance(value.get("text"), str)
    if content_type == "refusal":
        return isinstance(value.get("refusal"), str)
    return False


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
    return all(_is_responses_message_content(item) for item in content)


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
async def test_chat_ops_includes_gbnf_grammar_for_llama_server() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "{}"},
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIChatOpsProvider(
            settings=Settings(),
            client=client,
            base_url="http://localhost:8082",
            api_key="sk-no-key",
            model="Devstral-Small-2-24B",
        )
        await provider.complete_chat_ops(
            request=LLMChatRequest(messages=[ChatMessage(role="user", content="hi")]),
            system_prompt="sys",
        )

    assert captured["grammar"] == EDIT_OPS_PATCH_ONLY_GBNF
    assert "response_format" not in captured


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_ops_omits_gbnf_grammar_for_non_llama_server() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "{}"},
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIChatOpsProvider(
            settings=Settings(),
            client=client,
            base_url="https://example.test/v1",
            api_key="sk-no-key",
            model="Devstral-Small-2-24B",
        )
        await provider.complete_chat_ops(
            request=LLMChatRequest(messages=[ChatMessage(role="user", content="hi")]),
            system_prompt="sys",
        )

    assert "grammar" not in captured
    assert captured["response_format"] == EDIT_OPS_PATCH_ONLY_RESPONSE_FORMAT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_ops_uses_text_format_for_openai_responses() -> None:
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
                        "content": [{"type": "output_text", "text": "{}"}],
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAIChatOpsProvider(
            settings=Settings(),
            client=client,
            base_url="https://api.openai.com/v1",
            api_key="sk-no-key",
            model="gpt-5.2",
        )
        await provider.complete_chat_ops(
            request=LLMChatRequest(messages=[ChatMessage(role="user", content="hi")]),
            system_prompt="sys",
        )

    assert captured is not None
    assert "text" in captured
    text = captured["text"]
    assert "format" in text
    assert text["format"]["type"] == "json_schema"
    assert text["format"]["name"] == EDIT_OPS_PATCH_ONLY_RESPONSE_FORMAT["json_schema"]["name"]
    assert text["format"]["schema"] == EDIT_OPS_PATCH_ONLY_RESPONSE_FORMAT["json_schema"]["schema"]
    assert "response_format" not in captured
    assert "grammar" not in captured
    assert captured_url is not None
    assert captured_url.endswith("/responses")
