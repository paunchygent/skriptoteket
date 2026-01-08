from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.protocols.llm import (
    EditorChatHistoryHandlerProtocol,
    EditorChatHistoryResult,
)
from skriptoteket.web.api.v1.editor import chat as chat_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class EditorChatHistoryApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: AsyncMock,
        sessions: AsyncMock,
        maintainers: AsyncMock,
        handler: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._maintainers = maintainers
        self._handler = handler

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.REQUEST)
    def current_user_provider(self) -> CurrentUserProviderProtocol:
        return cast(CurrentUserProviderProtocol, self._current_user_provider)

    @provide(scope=Scope.REQUEST)
    def sessions(self) -> SessionRepositoryProtocol:
        return cast(SessionRepositoryProtocol, self._sessions)

    @provide(scope=Scope.REQUEST)
    def maintainers(self) -> ToolMaintainerRepositoryProtocol:
        return cast(ToolMaintainerRepositoryProtocol, self._maintainers)

    @provide(scope=Scope.REQUEST)
    def editor_chat_history_handler(self) -> EditorChatHistoryHandlerProtocol:
        return cast(EditorChatHistoryHandlerProtocol, self._handler)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def clock(now: datetime) -> ClockProtocol:
    return FixedClock(now=now)


@pytest.fixture
def current_user_provider() -> AsyncMock:
    provider = AsyncMock(spec=CurrentUserProviderProtocol)
    provider.get_current_user.return_value = None
    return provider


@pytest.fixture
def sessions() -> AsyncMock:
    repo = AsyncMock(spec=SessionRepositoryProtocol)
    repo.get_by_id.return_value = None
    return repo


@pytest.fixture
def maintainers() -> AsyncMock:
    repo = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    repo.is_maintainer.return_value = True
    return repo


@pytest.fixture
def handler() -> AsyncMock:
    return AsyncMock(spec=EditorChatHistoryHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    maintainers: AsyncMock,
    handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(chat_api.router, prefix="/api/v1/editor", tags=["editor"])

    container = make_async_container(
        EditorChatHistoryApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
            maintainers=maintainers,
            handler=handler,
        )
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_editor_chat_history_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/api/v1/editor/tools/{uuid4()}/chat")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_editor_chat_history_returns_messages(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.CONTRIBUTOR)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    tool_id = uuid4()
    base_version_id = uuid4()
    first_message_id = uuid4()
    second_message_id = uuid4()

    handler.handle.return_value = EditorChatHistoryResult(
        messages=[
            ToolSessionMessage(
                id=uuid4(),
                tool_session_id=uuid4(),
                message_id=first_message_id,
                role="user",
                content="Hej",
                meta=None,
                sequence=1,
                created_at=now,
            ),
            ToolSessionMessage(
                id=uuid4(),
                tool_session_id=uuid4(),
                message_id=second_message_id,
                role="assistant",
                content="Svar",
                meta=None,
                sequence=2,
                created_at=now,
            ),
        ],
        base_version_id=base_version_id,
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.get(f"/api/v1/editor/tools/{tool_id}/chat", params={"limit": 2})

    assert response.status_code == 200
    payload = response.json()
    expected_timestamp = now.isoformat().replace("+00:00", "Z")
    assert payload["base_version_id"] == str(base_version_id)
    assert payload["messages"] == [
        {
            "message_id": str(first_message_id),
            "role": "user",
            "content": "Hej",
            "created_at": expected_timestamp,
        },
        {
            "message_id": str(second_message_id),
            "role": "assistant",
            "content": "Svar",
            "created_at": expected_timestamp,
        },
    ]

    called_query = handler.handle.call_args.kwargs["query"]
    assert called_query.tool_id == tool_id
    assert called_query.limit == 2
