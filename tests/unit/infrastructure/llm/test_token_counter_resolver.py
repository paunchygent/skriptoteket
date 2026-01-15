from __future__ import annotations

import pytest

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.token_counter_resolver import (
    HeuristicTokenCounter,
    SettingsBasedTokenCounterResolver,
    TekkenTokenCounter,
)


@pytest.mark.unit
def test_token_counter_resolver_can_cache_per_instance() -> None:
    resolver = SettingsBasedTokenCounterResolver(settings=Settings())

    first = resolver.for_model(model="llama-3.1")
    second = resolver.for_model(model="llama-3.1")

    assert isinstance(first, HeuristicTokenCounter)
    assert first is second


@pytest.mark.unit
def test_token_counter_resolver_uses_packaged_tekken_when_available() -> None:
    pytest.importorskip("mistral_common")
    resolver = SettingsBasedTokenCounterResolver(
        settings=Settings(LLM_DEVSTRAL_TEKKEN_JSON_PATH=None)
    )

    counter = resolver.for_model(model="Devstral-Small-2-24B")

    assert isinstance(counter, TekkenTokenCounter)
