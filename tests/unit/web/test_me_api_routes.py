from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from skriptoteket.application.catalog.queries import ListRecentToolsResult
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ListRecentToolsHandlerProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.web.api.v1 import me as me_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class MeApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: AsyncMock,
        sessions: AsyncMock,
        list_handler: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._list_handler = list_handler

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
    def list_recent_tools_handler(self) -> ListRecentToolsHandlerProtocol:
        return cast(ListRecentToolsHandlerProtocol, self._list_handler)


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
def list_handler() -> AsyncMock:
    return AsyncMock(spec=ListRecentToolsHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    list_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(me_api.router)

    container = make_async_container(
        MeApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
            list_handler=list_handler,
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
async def test_recent_tools_default_limit(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    list_handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    list_handler.handle.return_value = ListRecentToolsResult(items=[])

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.get("/api/v1/me/recent-tools")

    assert response.status_code == 200
    list_handler.handle.assert_awaited_once()
    query = list_handler.handle.call_args.kwargs["query"]
    assert query.limit == 10


@pytest.mark.asyncio
async def test_recent_tools_custom_limit(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    list_handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    list_handler.handle.return_value = ListRecentToolsResult(items=[])

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.get("/api/v1/me/recent-tools?limit=5")

    assert response.status_code == 200
    list_handler.handle.assert_awaited_once()
    query = list_handler.handle.call_args.kwargs["query"]
    assert query.limit == 5
