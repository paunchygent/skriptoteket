from __future__ import annotations

from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model


def build_chat_payload(
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

    if is_gpt5_family_model(model=model):
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
