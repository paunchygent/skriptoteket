from __future__ import annotations

import pytest

from skriptoteket.infrastructure.llm.openai.payloads import build_chat_payload


@pytest.mark.unit
def test_build_chat_payload_uses_classic_max_tokens_for_non_gpt5() -> None:
    payload = build_chat_payload(
        model="Devstral-Small-2-24B",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="medium",
        stream=False,
    )

    assert payload["max_tokens"] == 123
    assert payload["temperature"] == 0.2
    assert "max_completion_tokens" not in payload


@pytest.mark.unit
def test_build_chat_payload_uses_max_completion_tokens_for_gpt5() -> None:
    payload = build_chat_payload(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort="medium",
        stream=False,
    )

    assert payload["max_completion_tokens"] == 123
    assert payload["reasoning_effort"] == "medium"
    assert "max_tokens" not in payload


@pytest.mark.unit
def test_build_chat_payload_omits_prompt_cache_params_when_disallowed() -> None:
    payload = build_chat_payload(
        model="Devstral-Small-2-24B",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=123,
        temperature=0.2,
        reasoning_effort=None,
        stream=False,
        cache_prompt=True,
        prompt_cache_retention="24h",
        prompt_cache_key="key",
        allow_prompt_cache_params=False,
    )

    assert payload["cache_prompt"] is True
    assert "prompt_cache_retention" not in payload
    assert "prompt_cache_key" not in payload
