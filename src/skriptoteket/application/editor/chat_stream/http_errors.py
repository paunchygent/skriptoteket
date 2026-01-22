"""HTTP error helpers for chat stream."""

from __future__ import annotations

import httpx


def is_context_window_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None:
        return False
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except (ValueError, httpx.ResponseNotRead):
        payload = None
    if payload is not None:
        haystack = str(payload)
    else:
        try:
            haystack = response.text
        except httpx.ResponseNotRead:
            return False
    return "exceed_context_size_error" in haystack.lower()
