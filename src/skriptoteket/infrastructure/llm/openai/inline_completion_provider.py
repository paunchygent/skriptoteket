from __future__ import annotations

import httpx
import structlog

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model
from skriptoteket.infrastructure.llm.openai.common import (
    is_local_llama_server,
    is_openai_api_base_url,
    merge_headers,
    normalize_base_url,
    resolve_prompt_cache_retention,
)
from skriptoteket.infrastructure.llm.openai.fim import build_fim_prompt
from skriptoteket.infrastructure.llm.openai.inline_completion_prompt import (
    build_delimited_inline_completion_prompt,
)
from skriptoteket.infrastructure.llm.openai.parsing import (
    extract_first_choice_content,
    extract_response_output_text,
)
from skriptoteket.infrastructure.llm.openai.payloads import (
    build_chat_payload,
    build_responses_payload,
)
from skriptoteket.protocols.llm import (
    InlineCompletionProviderProtocol,
    LLMCompletionRequest,
    LLMCompletionResponse,
)


class OpenAIInlineCompletionProvider(InlineCompletionProviderProtocol):
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
        self._environment = settings.ENVIRONMENT
        self._base_url = normalize_base_url(base_url=base_url or settings.LLM_COMPLETION_BASE_URL)
        self._api_key = (
            settings.OPENAI_LLM_COMPLETION_API_KEY if api_key is None else api_key
        ).strip()
        self._extra_headers = settings.LLM_COMPLETION_EXTRA_HEADERS
        self._model = (settings.LLM_COMPLETION_MODEL if model is None else model).strip()
        self._prompt_cache_key = settings.LLM_COMPLETION_PROMPT_CACHE_KEY.strip()
        self._allow_prompt_cache_params = not is_local_llama_server(base_url=self._base_url)
        self._use_responses_api = is_openai_api_base_url(base_url=self._base_url)
        self._prompt_cache_retention = resolve_prompt_cache_retention(
            settings=settings,
            configured_retention=settings.LLM_COMPLETION_PROMPT_CACHE_RETENTION,
            allow_prompt_cache_params=self._allow_prompt_cache_params,
            model=self._model,
            profile="inline_completion",
        )
        self._reasoning_effort = (
            settings.LLM_COMPLETION_REASONING_EFFORT
            if reasoning_effort is None
            else reasoning_effort
        )
        self._text_verbosity = settings.LLM_COMPLETION_TEXT_VERBOSITY
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
        logger = structlog.get_logger(__name__)
        if self._use_responses_api:
            url = f"{self._base_url}/responses"
        else:
            url = f"{self._base_url}/chat/completions"
        headers = merge_headers(api_key=self._api_key, extra_headers=self._extra_headers)

        user_prompt = build_fim_prompt(
            prefix=request.prefix,
            suffix=request.suffix,
            model=self._model,
        )
        if self._use_responses_api and is_gpt5_family_model(model=self._model):
            user_prompt = build_delimited_inline_completion_prompt(
                prefix=request.prefix,
                suffix=request.suffix,
                active_file=request.active_file,
            )

        if self._use_responses_api:
            request_payload = dict(
                build_responses_payload(
                    model=self._model,
                    messages=[{"role": "user", "content": user_prompt}],
                    instructions=system_prompt,
                    max_tokens=self._max_tokens,
                    temperature=self._temperature,
                    reasoning_effort=self._reasoning_effort,
                    text_verbosity=self._text_verbosity,
                    stream=False,
                    store=False,
                    truncation="auto",
                    stop=["\n```"],
                    prompt_cache_retention=self._prompt_cache_retention,
                    prompt_cache_key=self._prompt_cache_key,
                    allow_prompt_cache_params=self._allow_prompt_cache_params,
                )
            )
        else:
            request_payload = build_chat_payload(
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

        if self._environment != "production":
            logger.info(
                "inline_completion_payload_shape",
                model=self._model,
                base_url=self._base_url,
                use_responses_api=self._use_responses_api,
                prompt_format="delimited"
                if self._use_responses_api and is_gpt5_family_model(model=self._model)
                else "fim",
                has_reasoning="reasoning" in request_payload,
                has_text="text" in request_payload,
                has_stop="stop" in request_payload,
                has_prompt_cache_key="prompt_cache_key" in request_payload,
                has_prompt_cache_retention="prompt_cache_retention" in request_payload,
                store=request_payload.get("store"),
                truncation=request_payload.get("truncation"),
            )

        response = await self._client.post(
            url,
            headers=headers,
            json=request_payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        response_payload = response.json()
        if not isinstance(response_payload, dict):
            raise ValueError("Upstream LLM response is not an object")

        if self._use_responses_api:
            content, finish_reason = extract_response_output_text(response_payload)
        else:
            content, finish_reason = extract_first_choice_content(response_payload)
        return LLMCompletionResponse(completion=content, finish_reason=finish_reason)
