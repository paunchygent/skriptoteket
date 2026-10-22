from __future__ import annotations

import pytest

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.token_counter_resolver import (
    SettingsBasedTokenCounterResolver,
    TiktokenTokenCounter,
)


@pytest.mark.unit
@pytest.mark.parametrize("model", ["gpt-6-luna", "gpt-6.1-sol", "unknown-model"])
def test_every_model_gets_a_tiktoken_counter(model: str) -> None:
    counter = SettingsBasedTokenCounterResolver(settings=Settings()).for_model(model=model)

    assert isinstance(counter, TiktokenTokenCounter)
    assert counter.count_text("def f(): pass") > 0


@pytest.mark.unit
def test_token_counter_resolver_can_cache_per_instance() -> None:
    resolver = SettingsBasedTokenCounterResolver(settings=Settings())

    assert resolver.for_model(model="gpt-6-luna") is resolver.for_model(model="gpt-6-luna")


@pytest.mark.unit
def test_counter_adds_the_configured_message_overheads() -> None:
    settings = Settings(
        LLM_GPT5_SYSTEM_MESSAGE_OVERHEAD_TOKENS=7, LLM_GPT5_MESSAGE_OVERHEAD_TOKENS=5
    )
    counter = SettingsBasedTokenCounterResolver(settings=settings).for_model(model="gpt-6-luna")
    text_tokens = counter.count_text("hello world")

    assert counter.count_system_prompt(content="hello world") == 7 + text_tokens
    assert counter.count_chat_message(role="user", content="hello world") == 5 + text_tokens
    assert counter.count_chat_message(role="user", content="") == 5
    assert counter.count_system_prompt(content="") == 0


@pytest.mark.unit
def test_counter_truncates_by_tokens_from_either_end() -> None:
    counter = SettingsBasedTokenCounterResolver(settings=Settings()).for_model(model="gpt-6-luna")
    text = "alpha beta gamma delta epsilon"

    head = counter.truncate_text_head(text=text, max_tokens=2)
    tail = counter.truncate_text_tail(text=text, max_tokens=2)

    assert text.startswith(head) and counter.count_text(head) <= 2
    assert text.endswith(tail) and counter.count_text(tail) <= 2
    assert counter.truncate_text_head(text=text, max_tokens=0) == ""
