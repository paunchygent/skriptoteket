from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from skriptoteket.application.editor.chat_stream_orchestrator import _is_context_window_error


class _StreamingBody(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'{"error":"exceed_context_size_error"}'

    async def aclose(self) -> None:
        return None


@pytest.mark.unit
def test_is_context_window_error_returns_false_when_response_not_read() -> None:
    request = httpx.Request("POST", "https://example.test/chat/completions")
    response = httpx.Response(400, request=request, stream=_StreamingBody())
    exc = httpx.HTTPStatusError("Boom", request=request, response=response)

    assert _is_context_window_error(exc) is False
