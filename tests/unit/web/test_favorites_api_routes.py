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

from skriptoteket.application.favorites.commands import FavoriteStatusResult
from skriptoteket.application.favorites.queries import FavoriteCatalogItem, ListFavoritesResult
from skriptoteket.config import Settings
from skriptoteket.domain.favorites.models import FavoriteCatalogItemKind
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.favorites import (
    AddFavoriteHandlerProtocol,
    ListFavoritesHandlerProtocol,
    RemoveFavoriteHandlerProtocol,
)
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.web.api.v1 import favorites as favorites_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FavoritesApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: AsyncMock,
        sessions: AsyncMock,
        add_handler: AsyncMock,
        remove_handler: AsyncMock,
        list_handler: AsyncMock,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._add_handler = add_handler
        self._remove_handler = remove_handler
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
    def add_favorite_handler(self) -> AddFavoriteHandlerProtocol:
        return cast(AddFavoriteHandlerProtocol, self._add_handler)

    @provide(scope=Scope.REQUEST)
    def remove_favorite_handler(self) -> RemoveFavoriteHandlerProtocol:
        return cast(RemoveFavoriteHandlerProtocol, self._remove_handler)

    @provide(scope=Scope.REQUEST)
    def list_favorites_handler(self) -> ListFavoritesHandlerProtocol:
        return cast(ListFavoritesHandlerProtocol, self._list_handler)


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
def add_handler() -> AsyncMock:
    return AsyncMock(spec=AddFavoriteHandlerProtocol)


@pytest.fixture
def remove_handler() -> AsyncMock:
    return AsyncMock(spec=RemoveFavoriteHandlerProtocol)


@pytest.fixture
def list_handler() -> AsyncMock:
    return AsyncMock(spec=ListFavoritesHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    add_handler: AsyncMock,
    remove_handler: AsyncMock,
    list_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(favorites_api.router)

    container = make_async_container(
        FavoritesApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
            add_handler=add_handler,
            remove_handler=remove_handler,
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
async def test_favorites_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/favorites")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_favorite_requires_csrf(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/favorites/{uuid4()}",
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_add_favorite_success(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    add_handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)
    favorite_id = uuid4()

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    add_handler.handle.return_value = FavoriteStatusResult(id=favorite_id, is_favorite=True)

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/favorites/{favorite_id}",
        headers={"X-CSRF-Token": session.csrf_token},
    )

    assert response.status_code == 200
    assert response.json() == {"id": str(favorite_id), "is_favorite": True}

    add_handler.handle.assert_awaited_once()
    command = add_handler.handle.call_args.kwargs["command"]
    assert command.catalog_item_id == favorite_id


@pytest.mark.asyncio
async def test_remove_favorite_success(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    remove_handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)
    favorite_id = uuid4()

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    remove_handler.handle.return_value = FavoriteStatusResult(id=favorite_id, is_favorite=False)

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.delete(
        f"/api/v1/favorites/{favorite_id}",
        headers={"X-CSRF-Token": session.csrf_token},
    )

    assert response.status_code == 200
    assert response.json() == {"id": str(favorite_id), "is_favorite": False}

    remove_handler.handle.assert_awaited_once()
    command = remove_handler.handle.call_args.kwargs["command"]
    assert command.catalog_item_id == favorite_id


@pytest.mark.asyncio
async def test_list_favorites_returns_items(
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

    tool_id = uuid4()
    app_id = "demo.counter"

    list_handler.handle.return_value = ListFavoritesResult(
        items=[
            FavoriteCatalogItem(
                kind=FavoriteCatalogItemKind.TOOL,
                id=tool_id,
                slug="demo-tool",
                title="Demo",
                summary=None,
                is_favorite=True,
            ),
            FavoriteCatalogItem(
                kind=FavoriteCatalogItemKind.CURATED_APP,
                id=uuid4(),
                app_id=app_id,
                title="Counter",
                summary="Demo app",
                is_favorite=True,
            ),
        ]
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.get("/api/v1/favorites?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["kind"] == "tool"
    assert payload["items"][0]["id"] == str(tool_id)
    assert payload["items"][1]["kind"] == "curated_app"
    assert payload["items"][1]["app_id"] == app_id

    list_handler.handle.assert_awaited_once()
    query = list_handler.handle.call_args.kwargs["query"]
    assert query.limit == 5
