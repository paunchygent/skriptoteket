from __future__ import annotations

import json

import httpx
import pytest

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.openai.chat_ops_provider import OpenAIChatOpsProvider
from skriptoteket.infrastructure.llm.openai.grammars import (
    EDIT_OPS_PATCH_ONLY_GBNF,
    EDIT_OPS_PATCH_ONLY_RESPONSE_FORMAT,
)
from skriptoteket.protocols.llm import ChatMessage, LLMChatRequest


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
