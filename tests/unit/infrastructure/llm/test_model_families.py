from __future__ import annotations

import pytest

from skriptoteket.infrastructure.llm.model_families import is_gpt5_family_model


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("", False),
        ("devstral-small", False),
        ("gpt-5", True),
        ("gpt-5-mini", True),
        ("openai/gpt-5", True),
        ("openai/gpt-5-mini", True),
        ("OPENAI/GPT-5-MINI", True),
        ("gpt-5x", False),
        ("openai/gpt-5x", False),
    ],
)
def test_is_gpt5_family_model(model: str, expected: bool) -> None:
    assert is_gpt5_family_model(model=model) is expected
