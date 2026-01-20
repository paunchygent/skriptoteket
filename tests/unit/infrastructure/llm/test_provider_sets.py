from __future__ import annotations

import pytest

from skriptoteket.infrastructure.llm.provider_sets import is_remote_llm_endpoint


@pytest.mark.unit
@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("http://localhost:8082", False),
        ("  http://localhost:8082  ", False),
        ("http://127.0.0.1:8082", False),
        ("http://10.0.0.1:8082", False),
        ("http://192.168.1.50:8082", False),
        ("http://172.18.0.1:8082", False),
        ("http://169.254.10.10:8082", False),
        ("http://host.docker.internal:8082", False),
        ("http://gateway.docker.internal:8082", False),
        ("https://api.openai.com", True),
        ("http://8.8.8.8:8082", True),
        ("localhost:8082", True),
        ("", True),
        ("not a url", True),
    ],
)
def test_is_remote_llm_endpoint(base_url: str, expected: bool) -> None:
    assert is_remote_llm_endpoint(base_url) is expected
