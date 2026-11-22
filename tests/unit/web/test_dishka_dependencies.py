"""Unit tests for the public web Dishka dependency helpers.

Purpose:
    Lock the helper-level websocket resolution behavior introduced by ST-07-07.

Relationships:
    - Covers `skriptoteket.web.dishka_dependencies`.
    - Complements HTTP route tests that exercise the FastAPI `Depends` path.
    - Complements the websocket integration test that proves middleware wiring.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocket
from starlette.types import Message

from skriptoteket.config import Settings
from skriptoteket.web.dishka_dependencies import resolve_from_websocket


@pytest.mark.asyncio
async def test_resolve_from_websocket_reads_websocket_state_container() -> None:
    container = AsyncMock()
    expected = Settings()
    container.get.return_value = expected

    async def receive() -> Message:
        return {"type": "websocket.connect"}

    async def send(message: Message) -> None:
        return None

    websocket = WebSocket(
        scope={"type": "websocket", "state": {"dishka_container": container}},
        receive=receive,
        send=send,
    )

    resolved = await resolve_from_websocket(websocket, Settings)

    assert resolved is expected
    container.get.assert_awaited_once_with(Settings)
