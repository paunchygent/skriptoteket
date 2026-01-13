from __future__ import annotations

import pytest

from skriptoteket.config import Settings
from skriptoteket.infrastructure.llm.token_counter_resolver import (
    HeuristicTokenCounter,
    SettingsBasedTokenCounterResolver,
)


@pytest.mark.unit
def test_token_counter_resolver_can_cache_per_instance() -> None:
    resolver = SettingsBasedTokenCounterResolver(settings=Settings())

    first = resolver.for_model(model="llama-3.1")
    second = resolver.for_model(model="llama-3.1")

    assert isinstance(first, HeuristicTokenCounter)
    assert first is second
