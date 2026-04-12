from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.catalog.queries import ListRecentToolsResult
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ListRecentToolsHandlerProtocol
from skriptoteket.web.api.v1 import me as me_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class MeApiProvider(Provider):
    def __init__(
        self,
        *,
        list_handler: ListRecentToolsHandlerProtocol,
    ) -> None:
        super().__init__()
        self._list_handler = list_handler

    @provide(scope=Scope.REQUEST)
    def list_recent_tools_handler(self) -> ListRecentToolsHandlerProtocol:
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
def list_handler() -> AsyncMock:
    return AsyncMock(spec=ListRecentToolsHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    list_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(me_api.router)

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        MeApiProvider(
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
async def test_recent_tools_default_limit(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    list_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)
    list_handler.handle.return_value = ListRecentToolsResult(items=[])

    response = await client.get(
        "/api/v1/me/recent-tools",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    list_handler.handle.assert_awaited_once()
    query = list_handler.handle.call_args.kwargs["query"]
    assert query.limit == 10


@pytest.mark.asyncio
async def test_recent_tools_custom_limit(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    list_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)
    list_handler.handle.return_value = ListRecentToolsResult(items=[])

    response = await client.get(
        "/api/v1/me/recent-tools?limit=5",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    list_handler.handle.assert_awaited_once()
    query = list_handler.handle.call_args.kwargs["query"]
    assert query.limit == 5
