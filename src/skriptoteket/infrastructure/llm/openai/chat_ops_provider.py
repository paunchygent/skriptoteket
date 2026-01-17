from __future__ import annotations

import httpx
import structlog

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model
from skriptoteket.infrastructure.llm.openai.common import (
    is_local_llama_server,
    merge_headers,
    normalize_base_url,
    supports_gbnf_grammar,
)
from skriptoteket.infrastructure.llm.openai.grammars import (
    EDIT_OPS_PATCH_ONLY_GBNF,
    EDIT_OPS_PATCH_ONLY_RESPONSE_FORMAT,
)
from skriptoteket.infrastructure.llm.openai.parsing import extract_first_choice_content
from skriptoteket.infrastructure.llm.openai.payloads import build_chat_payload
from skriptoteket.protocols.llm import (
    ChatOpsProviderProtocol,
    LLMChatOpsResponse,
    LLMChatRequest,
)


class OpenAIChatOpsProvider(ChatOpsProviderProtocol):
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
        self._settings = settings
        self._base_url = normalize_base_url(base_url=base_url or settings.LLM_CHAT_OPS_BASE_URL)
        self._api_key = (
            settings.OPENAI_LLM_CHAT_OPS_API_KEY if api_key is None else api_key
        ).strip()
        self._prompt_cache_key = settings.LLM_CHAT_OPS_PROMPT_CACHE_KEY.strip()
        self._prompt_cache_retention = settings.LLM_CHAT_OPS_PROMPT_CACHE_RETENTION
        self._extra_headers = settings.LLM_CHAT_OPS_EXTRA_HEADERS
        self._allow_prompt_cache_params = not is_local_llama_server(base_url=self._base_url)
        self._model = (settings.LLM_CHAT_OPS_MODEL if model is None else model).strip()
        self._reasoning_effort = (
            settings.LLM_CHAT_OPS_REASONING_EFFORT if reasoning_effort is None else reasoning_effort
        )
        self._max_tokens = (
            settings.LLM_CHAT_OPS_GPT5_MAX_TOKENS
            if is_gpt5_family_model(model=self._model)
            else settings.LLM_CHAT_OPS_MAX_TOKENS
        )
        self._temperature = settings.LLM_CHAT_OPS_TEMPERATURE
        self._timeout = settings.LLM_CHAT_OPS_TIMEOUT_SECONDS
        self._client = client
        self._use_prompt_cache = is_local_llama_server(base_url=self._base_url)

    async def complete_chat_ops(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
    ) -> LLMChatOpsResponse:
        logger = structlog.get_logger(__name__)
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
            stream=False,
            cache_prompt=self._use_prompt_cache,
            prompt_cache_retention=self._prompt_cache_retention,
            prompt_cache_key=self._prompt_cache_key,
            allow_prompt_cache_params=self._allow_prompt_cache_params,
        )
        if supports_gbnf_grammar(base_url=self._base_url):
            payload["grammar"] = EDIT_OPS_PATCH_ONLY_GBNF
        else:
            payload["response_format"] = EDIT_OPS_PATCH_ONLY_RESPONSE_FORMAT
        if self._settings.ENVIRONMENT != "production":
            logger.info(
                "chat_ops_structured_output",
                model=self._model,
                base_url=self._base_url,
                grammar="grammar" in payload,
                response_format="response_format" in payload,
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
        return LLMChatOpsResponse(
            content=content,
            finish_reason=finish_reason,
            raw_payload=dict(payload),
        )
