from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest
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
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.web.api.v1 import apps_classroom_planner as planner_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class PlannerImportsApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: CurrentUserProviderProtocol,
        sessions: SessionRepositoryProtocol,
        import_handler: CreateClassListImportPreviewHandler,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._import_handler = import_handler

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.REQUEST)
    def current_user_provider(self) -> CurrentUserProviderProtocol:
        return self._current_user_provider

    @provide(scope=Scope.REQUEST)
    def sessions(self) -> SessionRepositoryProtocol:
        return self._sessions

    @provide(scope=Scope.REQUEST)
    def import_handler(self) -> CreateClassListImportPreviewHandler:
        return self._import_handler


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
def import_handler() -> AsyncMock:
    return AsyncMock(spec=CreateClassListImportPreviewHandler)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
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
        PlannerImportsApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
            import_handler=import_handler,
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
async def test_import_preview_requires_auth(client: httpx.AsyncClient) -> None:
    files = {"file": ("test.txt", b"content", "text/plain")}
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/rosters/import-preview", files=files
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_import_preview_requires_csrf(
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
    files = {"file": ("test.txt", b"content", "text/plain")}
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/rosters/import-preview", files=files
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_import_preview_success(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    import_handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    file_name = "test_class.txt"
    import_handler.handle.return_value = ClassListImportPreview(
        file_name=file_name,
        suggested_class_name="SA24D",
        parsed_students=[ParsedStudentRow(full_name="Alice Andersson", row_number=1)],
        ambiguous_rows=[],
    )

    correlation_id = "53f6d262-789c-4af4-a2c2-5ff5044d452f"
    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    files = {"file": (file_name, b"1. Alice Andersson", "text/plain")}
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/rosters/import-preview",
        files=files,
        headers={"X-CSRF-Token": session.csrf_token, "X-Correlation-ID": correlation_id},
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
