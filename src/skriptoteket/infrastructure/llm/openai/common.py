from __future__ import annotations

from urllib.parse import urlparse


def normalize_base_url(*, base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def is_local_llama_server(*, base_url: str) -> bool:
    parsed = urlparse(base_url)
    return parsed.port == 8082 and parsed.hostname in {"localhost", "127.0.0.1"}


def merge_headers(*, api_key: str, extra_headers: dict[str, str]) -> dict[str, str]:
    headers: dict[str, str] = dict(extra_headers) if extra_headers else {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers
