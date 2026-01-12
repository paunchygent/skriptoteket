from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from urllib.parse import urlparse

import httpx

from skriptoteket.config import Settings
from skriptoteket.protocols.llm import (
    ChatOpsProviderProtocol,
    ChatStreamProviderProtocol,
    InlineCompletionProviderProtocol,
    LLMChatOpsResponse,
    LLMChatRequest,
    LLMCompletionRequest,
    LLMCompletionResponse,
)


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def _is_local_llama_server(base_url: str) -> bool:
    parsed = urlparse(base_url)
    return parsed.port == 8082 and parsed.hostname in {"localhost", "127.0.0.1"}


def _resolve_fim_tokens(model: str) -> tuple[str, str, str]:
    model_lower = model.strip().lower()
    if "qwen" in model_lower:
        return ("<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>")
    if "codellama" in model_lower or "code-llama" in model_lower:
        return ("<PRE>", "<SUF>", "<MID>")
    if "starcoder" in model_lower:
        return ("<fim_prefix>", "<fim_suffix>", "<fim_middle>")
    return ("<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>")


def _build_fim_prompt(*, prefix: str, suffix: str, model: str) -> str:
    prefix_token, suffix_token, middle_token = _resolve_fim_tokens(model)
    return f"{prefix_token}{prefix}{suffix_token}{suffix}{middle_token}"


def _extract_first_choice_content(payload: Mapping[str, object]) -> tuple[str, str | None]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Upstream LLM response is missing choices")

    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("Upstream LLM response choice is not an object")

    finish_reason = first.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        finish_reason = None

    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content, finish_reason

    text = first.get("text")
    if isinstance(text, str):
        return text, finish_reason

    return "", finish_reason


def _extract_first_choice_delta(payload: Mapping[str, object]) -> tuple[str, str | None]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Upstream LLM stream chunk is missing choices")

    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("Upstream LLM stream chunk choice is not an object")

    finish_reason = first.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        finish_reason = None

    delta = first.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str):
            return content, finish_reason

        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") != "text":
                    continue
                text = part.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
            if text_parts:
                return "".join(text_parts), finish_reason

    text = first.get("text")
    if isinstance(text, str):
        return text, finish_reason

    return "", finish_reason


def _merge_headers(*, api_key: str, extra_headers: Mapping[str, str]) -> dict[str, str]:
    headers: dict[str, str] = dict(extra_headers) if extra_headers else {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _is_gpt5_family_model(model: str) -> bool:
    normalized = model.strip().lower()
    if not normalized:
        return False

    prefixes = ("gpt-5", "openai/gpt-5")
    for prefix in prefixes:
        if not normalized.startswith(prefix):
            continue
        end = len(prefix)
        if end == len(normalized) or normalized[end] in "-_.":
            return True

    return False


def _build_chat_payload(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    reasoning_effort: str | None,
    stream: bool,
    stop: list[str] | None = None,
    cache_prompt: bool = False,
    prompt_cache_retention: str | None = None,
    prompt_cache_key: str | None = None,
    allow_prompt_cache_params: bool = True,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }

    if _is_gpt5_family_model(model):
        payload["max_completion_tokens"] = max_tokens
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
    else:
        payload["max_tokens"] = max_tokens
        payload["temperature"] = temperature

    if stop:
        payload["stop"] = stop
    if cache_prompt:
        payload["cache_prompt"] = True
    if allow_prompt_cache_params:
        if prompt_cache_retention:
            payload["prompt_cache_retention"] = prompt_cache_retention
        if prompt_cache_key:
            payload["prompt_cache_key"] = prompt_cache_key

    return payload


class OpenAIInlineCompletionProvider(InlineCompletionProviderProtocol):
    def __init__(self, *, settings: Settings, client: httpx.AsyncClient) -> None:
        self._base_url = _normalize_base_url(settings.LLM_COMPLETION_BASE_URL)
        self._api_key = settings.OPENAI_LLM_COMPLETION_API_KEY.strip()
        self._prompt_cache_key = settings.LLM_COMPLETION_PROMPT_CACHE_KEY.strip()
        self._prompt_cache_retention = settings.LLM_COMPLETION_PROMPT_CACHE_RETENTION
        self._extra_headers = settings.LLM_COMPLETION_EXTRA_HEADERS
        self._allow_prompt_cache_params = not _is_local_llama_server(self._base_url)
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
        headers = _merge_headers(api_key=self._api_key, extra_headers=self._extra_headers)

        user_prompt = _build_fim_prompt(
            prefix=request.prefix,
            suffix=request.suffix,
            model=self._model,
        )

        payload = _build_chat_payload(
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

        content, finish_reason = _extract_first_choice_content(payload)
        return LLMCompletionResponse(completion=content, finish_reason=finish_reason)


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
        self._base_url = _normalize_base_url(base_url or settings.LLM_CHAT_BASE_URL)
        self._api_key = (settings.OPENAI_LLM_CHAT_API_KEY if api_key is None else api_key).strip()
        self._prompt_cache_key = settings.LLM_CHAT_PROMPT_CACHE_KEY.strip()
        self._prompt_cache_retention = settings.LLM_CHAT_PROMPT_CACHE_RETENTION
        self._extra_headers = settings.LLM_CHAT_EXTRA_HEADERS
        self._allow_prompt_cache_params = not _is_local_llama_server(self._base_url)
        self._model = (settings.LLM_CHAT_MODEL if model is None else model).strip()
        self._reasoning_effort = (
            settings.LLM_CHAT_REASONING_EFFORT if reasoning_effort is None else reasoning_effort
        )
        self._max_tokens = settings.LLM_CHAT_MAX_TOKENS
        self._temperature = settings.LLM_CHAT_TEMPERATURE
        self._timeout = settings.LLM_CHAT_TIMEOUT_SECONDS
        self._client = client
        self._use_prompt_cache = _is_local_llama_server(self._base_url)

    async def stream_chat(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
    ) -> AsyncIterator[str]:
        url = f"{self._base_url}/chat/completions"
        headers = _merge_headers(api_key=self._api_key, extra_headers=self._extra_headers)

        response_messages = [{"role": "system", "content": system_prompt}]
        response_messages.extend(
            {"role": message.role, "content": message.content} for message in request.messages
        )

        payload = _build_chat_payload(
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
                    delta, _finish_reason = _extract_first_choice_delta(payload)
                except ValueError:
                    continue
                if delta:
                    yield delta


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
        self._base_url = _normalize_base_url(base_url or settings.LLM_CHAT_OPS_BASE_URL)
        self._api_key = (
            settings.OPENAI_LLM_CHAT_OPS_API_KEY if api_key is None else api_key
        ).strip()
        self._prompt_cache_key = settings.LLM_CHAT_OPS_PROMPT_CACHE_KEY.strip()
        self._prompt_cache_retention = settings.LLM_CHAT_OPS_PROMPT_CACHE_RETENTION
        self._extra_headers = settings.LLM_CHAT_OPS_EXTRA_HEADERS
        self._allow_prompt_cache_params = not _is_local_llama_server(self._base_url)
        self._model = (settings.LLM_CHAT_OPS_MODEL if model is None else model).strip()
        self._reasoning_effort = (
            settings.LLM_CHAT_OPS_REASONING_EFFORT if reasoning_effort is None else reasoning_effort
        )
        self._max_tokens = (
            settings.LLM_CHAT_OPS_GPT5_MAX_TOKENS
            if _is_gpt5_family_model(self._model)
            else settings.LLM_CHAT_OPS_MAX_TOKENS
        )
        self._temperature = settings.LLM_CHAT_OPS_TEMPERATURE
        self._timeout = settings.LLM_CHAT_OPS_TIMEOUT_SECONDS
        self._client = client
        self._use_prompt_cache = _is_local_llama_server(self._base_url)

    async def complete_chat_ops(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
    ) -> LLMChatOpsResponse:
        url = f"{self._base_url}/chat/completions"
        headers = _merge_headers(api_key=self._api_key, extra_headers=self._extra_headers)

        response_messages = [{"role": "system", "content": system_prompt}]
        response_messages.extend(
            {"role": message.role, "content": message.content} for message in request.messages
        )

        payload = _build_chat_payload(
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

        content, finish_reason = _extract_first_choice_content(payload)
        return LLMChatOpsResponse(
            content=content,
            finish_reason=finish_reason,
            raw_payload=dict(payload),
        )
