from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.favorites.commands import FavoriteStatusResult
from skriptoteket.application.favorites.queries import FavoriteCatalogItem, ListFavoritesResult
from skriptoteket.config import Settings
from skriptoteket.domain.favorites.models import FavoriteCatalogItemKind
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.favorites import (
    AddFavoriteHandlerProtocol,
    ListFavoritesHandlerProtocol,
    RemoveFavoriteHandlerProtocol,
)
from skriptoteket.web.api.v1 import favorites as favorites_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class FavoritesApiProvider(Provider):
    def __init__(
        self,
        *,
        add_handler: AddFavoriteHandlerProtocol,
        remove_handler: RemoveFavoriteHandlerProtocol,
        list_handler: ListFavoritesHandlerProtocol,
    ) -> None:
        super().__init__()
        self._add_handler = add_handler
        self._remove_handler = remove_handler
        self._list_handler = list_handler

    @provide(scope=Scope.REQUEST)
    def add_favorite_handler(self) -> AddFavoriteHandlerProtocol:
        return self._add_handler

    @provide(scope=Scope.REQUEST)
    def remove_favorite_handler(self) -> RemoveFavoriteHandlerProtocol:
        return self._remove_handler

    @provide(scope=Scope.REQUEST)
    def list_favorites_handler(self) -> ListFavoritesHandlerProtocol:
        return self._list_handler


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def settings(private_key: rsa.RSAPrivateKey) -> Settings:
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    settings = Settings()
    settings.HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY = public_key.decode("utf-8")
    return settings


@pytest.fixture
def clock(now: datetime) -> ClockStub:
    return ClockStub(now=now)


@pytest.fixture
def users() -> UserRepositoryStub:
    return UserRepositoryStub()


@pytest.fixture
def profiles() -> ProfileRepositoryStub:
    return ProfileRepositoryStub()


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
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    add_handler: AsyncMock,
    remove_handler: AsyncMock,
    list_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(favorites_api.router)

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        FavoritesApiProvider(
            add_handler=add_handler,
            remove_handler=remove_handler,
            list_handler=list_handler,
        ),
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
async def test_add_favorite_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        f"/api/v1/favorites/{uuid4()}",
        headers={"X-CSRF-Token": "stale-local-csrf"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_favorite_success(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    add_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)
    favorite_id = uuid4()

    add_handler.handle.return_value = FavoriteStatusResult(id=favorite_id, is_favorite=True)

    response = await client.post(
        f"/api/v1/favorites/{favorite_id}",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    assert response.json() == {"id": str(favorite_id), "is_favorite": True}

    add_handler.handle.assert_awaited_once()
    command = add_handler.handle.call_args.kwargs["command"]
    assert command.catalog_item_id == favorite_id


@pytest.mark.asyncio
async def test_remove_favorite_success(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    remove_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)
    favorite_id = uuid4()

    remove_handler.handle.return_value = FavoriteStatusResult(id=favorite_id, is_favorite=False)

    response = await client.delete(
        f"/api/v1/favorites/{favorite_id}",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    assert response.json() == {"id": str(favorite_id), "is_favorite": False}

    remove_handler.handle.assert_awaited_once()
    command = remove_handler.handle.call_args.kwargs["command"]
    assert command.catalog_item_id == favorite_id


@pytest.mark.asyncio
async def test_list_favorites_returns_items(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    list_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)

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

    response = await client.get(
        "/api/v1/favorites?limit=5",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["kind"] == "tool"
    assert payload["items"][0]["id"] == str(tool_id)
    assert payload["items"][1]["kind"] == "curated_app"
    assert payload["items"][1]["app_id"] == app_id

    list_handler.handle.assert_awaited_once()
    query = list_handler.handle.call_args.kwargs["query"]
    assert query.limit == 5
