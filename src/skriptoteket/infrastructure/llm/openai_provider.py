from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from urllib.parse import urlparse

import httpx

from skriptoteket.config import Settings
from skriptoteket.protocols.llm import (
    ChatStreamProviderProtocol,
    EditSuggestionProviderProtocol,
    InlineCompletionProviderProtocol,
    LLMChatRequest,
    LLMCompletionRequest,
    LLMCompletionResponse,
    LLMEditRequest,
    LLMEditResponse,
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


class OpenAIInlineCompletionProvider(InlineCompletionProviderProtocol):
    def __init__(self, *, settings: Settings, client: httpx.AsyncClient) -> None:
        self._base_url = _normalize_base_url(settings.LLM_COMPLETION_BASE_URL)
        self._api_key = settings.OPENAI_LLM_COMPLETION_API_KEY.strip()
        self._model = settings.LLM_COMPLETION_MODEL.strip()
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
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        user_prompt = _build_fim_prompt(
            prefix=request.prefix,
            suffix=request.suffix,
            model=self._model,
        )

        response = await self._client.post(
            url,
            headers=headers,
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "stop": ["\n```"],
                "stream": False,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Upstream LLM response is not an object")

        content, finish_reason = _extract_first_choice_content(payload)
        return LLMCompletionResponse(completion=content, finish_reason=finish_reason)


class OpenAIEditSuggestionProvider(EditSuggestionProviderProtocol):
    def __init__(self, *, settings: Settings, client: httpx.AsyncClient) -> None:
        self._base_url = _normalize_base_url(settings.LLM_EDIT_BASE_URL)
        self._api_key = settings.OPENAI_LLM_EDIT_API_KEY.strip()
        self._model = settings.LLM_EDIT_MODEL.strip()
        self._max_tokens = settings.LLM_EDIT_MAX_TOKENS
        self._temperature = settings.LLM_EDIT_TEMPERATURE
        self._timeout = settings.LLM_EDIT_TIMEOUT_SECONDS
        self._client = client

    async def suggest_edits(
        self,
        *,
        request: LLMEditRequest,
        system_prompt: str,
    ) -> LLMEditResponse:
        url = f"{self._base_url}/chat/completions"
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        instruction = request.instruction or ""
        user_prompt = (
            "Instruction:\n"
            f"{instruction}\n\n"
            "Selected text:\n"
            f"{request.selection}\n\n"
            "Context before selection:\n"
            f"{request.prefix}\n\n"
            "Context after selection:\n"
            f"{request.suffix}\n"
        )

        response = await self._client.post(
            url,
            headers=headers,
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "stop": ["\n```"],
                "stream": False,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Upstream LLM response is not an object")

        content, finish_reason = _extract_first_choice_content(payload)
        return LLMEditResponse(suggestion=content, finish_reason=finish_reason)


class OpenAIChatStreamProvider(ChatStreamProviderProtocol):
    def __init__(self, *, settings: Settings, client: httpx.AsyncClient) -> None:
        self._base_url = _normalize_base_url(settings.LLM_CHAT_BASE_URL)
        self._api_key = settings.OPENAI_LLM_CHAT_API_KEY.strip()
        self._model = settings.LLM_CHAT_MODEL.strip()
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
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        response_messages = [{"role": "system", "content": system_prompt}]
        response_messages.extend(
            {"role": message.role, "content": message.content} for message in request.messages
        )

        async with self._client.stream(
            "POST",
            url,
            headers=headers,
            json={
                "model": self._model,
                "messages": response_messages,
                "max_tokens": self._max_tokens,
                "temperature": self._temperature,
                "stream": True,
                **({"cache_prompt": True} if self._use_prompt_cache else {}),
            },
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

                payload = json.loads(data)
                if not isinstance(payload, dict):
                    raise ValueError("Upstream LLM stream chunk is not an object")

                delta, _finish_reason = _extract_first_choice_delta(payload)
                if delta:
                    yield delta
