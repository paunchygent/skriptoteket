"""Route tests for observability endpoints under the public Dishka adapter.

Purpose:
    Prove `/healthz` and `/metrics` resolve dependencies through FastAPI
    `Depends` + `request.state.dishka_container` rather than the retired hybrid
    Dishka/FastAPI wrapper.

Relationships:
    - Exercises `skriptoteket.web.routes.observability`.
    - Uses `starlette-dishka` middleware setup, matching the production web app.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import SessionRepositoryProtocol, UserRepositoryProtocol
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from skriptoteket.web.routes import observability as observability_routes


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class ObservabilityProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        engine: AsyncEngine,
        sessions: SessionRepositoryProtocol,
        users: UserRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._engine = engine
        self._sessions = sessions
        self._users = users
        self._clock = clock

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def engine(self) -> AsyncEngine:
        return self._engine

    @provide(scope=Scope.REQUEST)
    def sessions(self) -> SessionRepositoryProtocol:
        return self._sessions

    @provide(scope=Scope.REQUEST)
    def users(self) -> UserRepositoryProtocol:
        return self._users

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock


@pytest.fixture
def settings() -> Settings:
    return Settings.model_construct(
        APP_NAME="Skriptoteket",
        APP_VERSION="0.2.0",
        SERVICE_NAME="skriptoteket",
        ENVIRONMENT="test",
        EMAIL_PROVIDER="smtp",
        HEALTHZ_SMTP_CHECK_ENABLED=True,
        ARTIFACTS_ROOT=Settings().ARTIFACTS_ROOT,
    )


@pytest.fixture
def engine() -> AsyncMock:
    return AsyncMock(spec=AsyncEngine)


@pytest.fixture
def sessions() -> AsyncMock:
    repo = AsyncMock(spec=SessionRepositoryProtocol)
    repo.count_active.return_value = 3
    return repo


@pytest.fixture
def users() -> AsyncMock:
    repo = AsyncMock(spec=UserRepositoryProtocol)
    repo.count_active_by_role.return_value = {}
    return repo


@pytest.fixture
def clock() -> ClockProtocol:
    return FixedClock(datetime(2026, 3, 29, 12, 0, tzinfo=UTC))


@pytest.fixture
def app(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    engine: AsyncMock,
    sessions: AsyncMock,
    users: AsyncMock,
    clock: ClockProtocol,
) -> FastAPI:
    monkeypatch.setattr(
        observability_routes,
        "check_database",
        AsyncMock(return_value=("healthy", None)),
    )
    monkeypatch.setattr(
        observability_routes,
        "check_smtp",
        AsyncMock(return_value=("healthy", None)),
    )
    monkeypatch.setattr(
        observability_routes,
        "get_session_file_usage",
        lambda *, artifacts_root: SimpleNamespace(bytes_total=42, files=7),
    )

    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(observability_routes.router)

    container = make_async_container(
        ObservabilityProvider(
            settings=settings,
            engine=engine,
            sessions=sessions,
            users=users,
            clock=clock,
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
async def test_healthz_uses_public_request_state_adapter(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_metrics_uses_public_request_state_adapter(
    client: httpx.AsyncClient,
    sessions: AsyncMock,
    users: AsyncMock,
) -> None:
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "session_files_bytes_total" in response.text
    sessions.count_active.assert_awaited_once()
    users.count_active_by_role.assert_awaited_once()
