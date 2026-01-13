from __future__ import annotations

import httpx

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.openai.common import (
    is_local_llama_server,
    merge_headers,
    normalize_base_url,
)
from skriptoteket.infrastructure.llm.openai.fim import build_fim_prompt
from skriptoteket.infrastructure.llm.openai.parsing import extract_first_choice_content
from skriptoteket.infrastructure.llm.openai.payloads import build_chat_payload
from skriptoteket.protocols.llm import (
    InlineCompletionProviderProtocol,
    LLMCompletionRequest,
    LLMCompletionResponse,
)


class OpenAIInlineCompletionProvider(InlineCompletionProviderProtocol):
    def __init__(self, *, settings: Settings, client: httpx.AsyncClient) -> None:
        self._base_url = normalize_base_url(base_url=settings.LLM_COMPLETION_BASE_URL)
        self._api_key = settings.OPENAI_LLM_COMPLETION_API_KEY.strip()
        self._prompt_cache_key = settings.LLM_COMPLETION_PROMPT_CACHE_KEY.strip()
        self._prompt_cache_retention = settings.LLM_COMPLETION_PROMPT_CACHE_RETENTION
        self._extra_headers = settings.LLM_COMPLETION_EXTRA_HEADERS
        self._allow_prompt_cache_params = not is_local_llama_server(base_url=self._base_url)
        self._model = settings.LLM_COMPLETION_MODEL.strip()
        self._reasoning_effort = settings.LLM_COMPLETION_REASONING_EFFORT
        self._max_tokens = settings.LLM_COMPLETION_MAX_TOKENS
        self._temperature = settings.LLM_COMPLETION_TEMPERATURE
        self._timeout = settings.LLM_COMPLETION_TIMEOUT_SECONDS
        self._client = client

    async def complete_inline(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
    ) -> LLMCompletionResponse:
        url = f"{self._base_url}/chat/completions"
        headers = merge_headers(api_key=self._api_key, extra_headers=self._extra_headers)

        user_prompt = build_fim_prompt(
            prefix=request.prefix,
            suffix=request.suffix,
            model=self._model,
        )

        payload = build_chat_payload(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            reasoning_effort=self._reasoning_effort,
            stream=False,
            stop=["\n```"],
            prompt_cache_retention=self._prompt_cache_retention,
            prompt_cache_key=self._prompt_cache_key,
            allow_prompt_cache_params=self._allow_prompt_cache_params,
        )

        response = await self._client.post(
            url,
            headers=headers,
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Upstream LLM response is not an object")

        content, finish_reason = extract_first_choice_content(payload)
        return LLMCompletionResponse(completion=content, finish_reason=finish_reason)
