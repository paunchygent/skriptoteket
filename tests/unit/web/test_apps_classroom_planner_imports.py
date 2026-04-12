from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.classroom_planner.handlers.imports import (
    CreateClassListImportPreviewHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.import_contracts import (
    ClassListImportPreview,
    ParsedStudentRow,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_classroom_planner as planner_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class PlannerImportsApiProvider(Provider):
    def __init__(
        self,
        *,
        import_handler: CreateClassListImportPreviewHandler,
    ) -> None:
        super().__init__()
        self._import_handler = import_handler

    @provide(scope=Scope.REQUEST)
    def import_handler(self) -> CreateClassListImportPreviewHandler:
        return self._import_handler


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
def import_handler() -> AsyncMock:
    return AsyncMock(spec=CreateClassListImportPreviewHandler)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    import_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def attach_correlation_id(request, call_next):  # type: ignore[no-untyped-def]
        header_value = request.headers.get("X-Correlation-ID")
        if header_value:
            request.state.correlation_id = UUID(header_value)
        return await call_next(request)

    app.middleware("http")(error_handler_middleware)
    app.include_router(planner_api.router)

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        PlannerImportsApiProvider(
            import_handler=import_handler,
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
async def test_import_preview_requires_auth(client: httpx.AsyncClient) -> None:
    files = {"file": ("test.txt", b"content", "text/plain")}
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/rosters/import-preview", files=files
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_import_preview_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
) -> None:
    files = {"file": ("test.txt", b"content", "text/plain")}
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/rosters/import-preview",
        files=files,
        headers={"X-CSRF-Token": "stale-local-csrf"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_import_preview_success(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    import_handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)

    file_name = "test_class.txt"
    import_handler.handle.return_value = ClassListImportPreview(
        file_name=file_name,
        suggested_class_name="SA24D",
        parsed_students=[ParsedStudentRow(full_name="Alice Andersson", row_number=1)],
        ambiguous_rows=[],
    )

    correlation_id = "53f6d262-789c-4af4-a2c2-5ff5044d452f"
    files = {"file": (file_name, b"1. Alice Andersson", "text/plain")}
    headers = signed_huleedu_headers(private_key=private_key, clock=clock)
    headers["X-Correlation-ID"] = correlation_id
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/rosters/import-preview",
        files=files,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == file_name
    assert data["suggested_class_name"] == "SA24D"
    assert len(data["parsed_students"]) == 1
    assert data["parsed_students"][0]["full_name"] == "Alice Andersson"

    import_handler.handle.assert_awaited_once()
    kwargs = import_handler.handle.call_args.kwargs
    assert kwargs["file_name"] == file_name
    assert kwargs["content_type"] == "text/plain"
    assert kwargs["file_content"] == b"1. Alice Andersson"
    assert kwargs["correlation_id"] == correlation_id
