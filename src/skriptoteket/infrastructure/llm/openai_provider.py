from __future__ import annotations

from collections.abc import Mapping

import httpx

from skriptoteket.config import Settings
from skriptoteket.protocols.llm import (
    InlineCompletionProviderProtocol,
    LLMCompletionRequest,
    LLMCompletionResponse,
)


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


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


class OpenAIInlineCompletionProvider(InlineCompletionProviderProtocol):
    def __init__(self, *, settings: Settings, client: httpx.AsyncClient) -> None:
        self._base_url = _normalize_base_url(settings.LLM_COMPLETION_BASE_URL)
        self._api_key = settings.OPENAI_LLM_COMPLETION_API_KEY.strip()
        self._model = settings.LLM_COMPLETION_MODEL.strip()
        self._max_tokens = settings.LLM_COMPLETION_MAX_TOKENS
        self._temperature = settings.LLM_COMPLETION_TEMPERATURE
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
                "stop": ["```"],
                "stream": False,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Upstream LLM response is not an object")

        content, finish_reason = _extract_first_choice_content(payload)
        return LLMCompletionResponse(completion=content, finish_reason=finish_reason)
