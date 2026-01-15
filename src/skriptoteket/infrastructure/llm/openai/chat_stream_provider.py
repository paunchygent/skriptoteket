from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model
from skriptoteket.infrastructure.llm.openai.common import (
    is_local_llama_server,
    merge_headers,
    normalize_base_url,
)
from skriptoteket.infrastructure.llm.openai.parsing import extract_first_choice_delta
from skriptoteket.infrastructure.llm.openai.payloads import build_chat_payload
from skriptoteket.protocols.llm import (
    ChatStreamProviderProtocol,
    LLMChatRequest,
)


class OpenAIChatStreamProvider(ChatStreamProviderProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        client: httpx.AsyncClient,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self._base_url = normalize_base_url(base_url=base_url or settings.LLM_CHAT_BASE_URL)
        self._api_key = (settings.OPENAI_LLM_CHAT_API_KEY if api_key is None else api_key).strip()
        self._prompt_cache_key = settings.LLM_CHAT_PROMPT_CACHE_KEY.strip()
        self._prompt_cache_retention = settings.LLM_CHAT_PROMPT_CACHE_RETENTION
        self._extra_headers = settings.LLM_CHAT_EXTRA_HEADERS
        self._allow_prompt_cache_params = not is_local_llama_server(base_url=self._base_url)
        self._model = (settings.LLM_CHAT_MODEL if model is None else model).strip()
        self._reasoning_effort = (
            settings.LLM_CHAT_REASONING_EFFORT if reasoning_effort is None else reasoning_effort
        )
        self._max_tokens = (
            settings.LLM_CHAT_GPT5_MAX_TOKENS
            if is_gpt5_family_model(model=self._model)
            else settings.LLM_CHAT_MAX_TOKENS
        )
        self._temperature = settings.LLM_CHAT_TEMPERATURE
        self._timeout = settings.LLM_CHAT_TIMEOUT_SECONDS
        self._client = client
        self._use_prompt_cache = is_local_llama_server(base_url=self._base_url)

    async def stream_chat(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
    ) -> AsyncIterator[str]:
        url = f"{self._base_url}/chat/completions"
        headers = merge_headers(api_key=self._api_key, extra_headers=self._extra_headers)

        response_messages = [{"role": "system", "content": system_prompt}]
        response_messages.extend(
            {"role": message.role, "content": message.content} for message in request.messages
        )

        payload = build_chat_payload(
            model=self._model,
            messages=response_messages,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            reasoning_effort=self._reasoning_effort,
            stream=True,
            cache_prompt=self._use_prompt_cache,
            prompt_cache_retention=self._prompt_cache_retention,
            prompt_cache_key=self._prompt_cache_key,
            allow_prompt_cache_params=self._allow_prompt_cache_params,
        )

        async with self._client.stream(
            "POST",
            url,
            headers=headers,
            json=payload,
            timeout=self._timeout,
        ) as response:
            if response.status_code >= 400:
                await response.aread()
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                if "error" in payload:
                    raise ValueError("Upstream LLM stream chunk includes an error payload")

                try:
                    delta, _finish_reason = extract_first_choice_delta(payload)
                except ValueError:
                    continue
                if delta:
                    yield delta
