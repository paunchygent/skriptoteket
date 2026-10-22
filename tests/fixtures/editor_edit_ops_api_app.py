"""Shared fixtures for editor edit-ops route tests.

Purpose:
    Provide the FastAPI/Dishka test app, protocol stubs and virtual-file
    builder used by the edit-ops generation and preview/apply route tests.

Relationships:
    - Exercises `skriptoteket.web.api.v1.editor.edit_ops` with Dishka protocol
      stubs and the HuleEdu app-projection fixtures.
    - Keeps split test modules below the repo file-size budget.
"""

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

from skriptoteket.config import Settings
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.llm import (
    EditOpsApplyHandlerProtocol,
    EditOpsHandlerProtocol,
    EditOpsPreviewHandlerProtocol,
)
from skriptoteket.web.api.v1.editor import edit_ops as edit_ops_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
)


class EditorEditOpsApiProvider(Provider):
    def __init__(
        self,
        *,
        maintainers: ToolMaintainerRepositoryProtocol,
        handler: EditOpsHandlerProtocol,
        preview_handler: EditOpsPreviewHandlerProtocol,
        apply_handler: EditOpsApplyHandlerProtocol,
    ) -> None:
        super().__init__()
        self._maintainers = maintainers
        self._handler = handler
        self._preview_handler = preview_handler
        self._apply_handler = apply_handler

    @provide(scope=Scope.REQUEST)
    def maintainers(self) -> ToolMaintainerRepositoryProtocol:
        return self._maintainers

    @provide(scope=Scope.REQUEST)
    def edit_ops_handler(self) -> EditOpsHandlerProtocol:
        return self._handler

    @provide(scope=Scope.REQUEST)
    def edit_ops_preview_handler(self) -> EditOpsPreviewHandlerProtocol:
        return self._preview_handler

    @provide(scope=Scope.REQUEST)
    def edit_ops_apply_handler(self) -> EditOpsApplyHandlerProtocol:
        return self._apply_handler


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
def maintainers() -> AsyncMock:
    repo = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    repo.is_maintainer.return_value = True
    return repo


@pytest.fixture
def handler() -> AsyncMock:
    return AsyncMock(spec=EditOpsHandlerProtocol)


@pytest.fixture
def preview_handler() -> AsyncMock:
    return AsyncMock(spec=EditOpsPreviewHandlerProtocol)


@pytest.fixture
def apply_handler() -> AsyncMock:
    return AsyncMock(spec=EditOpsApplyHandlerProtocol)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    maintainers: AsyncMock,
    handler: AsyncMock,
    preview_handler: AsyncMock,
    apply_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(edit_ops_api.router, prefix="/api/v1/editor", tags=["editor"])

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        EditorEditOpsApiProvider(
            maintainers=maintainers,
            handler=handler,
            preview_handler=preview_handler,
            apply_handler=apply_handler,
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
