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
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette_dishka import setup_dishka

from skriptoteket.config import Settings
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
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
        users: UserRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._engine = engine
        self._users = users
        self._clock = clock

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def engine(self) -> AsyncEngine:
        return self._engine

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
    return _build_app(
        settings=settings,
        engine=engine,
        users=users,
        clock=clock,
    )


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
    assert response.json()["environment"] == "test"


@pytest.mark.asyncio
async def test_metrics_uses_public_request_state_adapter(
    client: httpx.AsyncClient,
    users: AsyncMock,
) -> None:
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "session_files_bytes_total" in response.text
    assert "skriptoteket_auth_context_verifications_total" in response.text
    users.count_active_by_role.assert_awaited_once()


@pytest.mark.asyncio
async def test_healthz_minimizes_public_payload_in_production(
    monkeypatch: pytest.MonkeyPatch,
    engine: AsyncMock,
    users: AsyncMock,
    clock: ClockProtocol,
) -> None:
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
    production_settings = Settings.model_construct(
        APP_NAME="Skriptoteket",
        APP_VERSION="0.2.0",
        SERVICE_NAME="skriptoteket",
        ENVIRONMENT="production",
        EMAIL_PROVIDER="smtp",
        HEALTHZ_SMTP_CHECK_ENABLED=True,
        HEALTHZ_DETAILED_RESPONSE=None,
        ARTIFACTS_ROOT=Settings().ARTIFACTS_ROOT,
    )
    app = _build_app(
        settings=production_settings,
        engine=engine,
        users=users,
        clock=clock,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "message": "Service is healthy",
    }


@pytest.mark.asyncio
async def test_metrics_skip_identity_gauges_in_production(
    monkeypatch: pytest.MonkeyPatch,
    engine: AsyncMock,
    users: AsyncMock,
    clock: ClockProtocol,
) -> None:
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
    registry = CollectorRegistry()
    monkeypatch.setattr(
        observability_routes,
        "get_metrics",
        lambda: {
            "http_requests_total": Counter(
                "skriptoteket_http_requests_total",
                "Total HTTP requests",
                ["method", "endpoint", "status_code"],
                registry=registry,
            ),
            "http_request_duration_seconds": Histogram(
                "skriptoteket_http_request_duration_seconds",
                "HTTP request duration in seconds",
                ["method", "endpoint"],
                registry=registry,
            ),
            "session_files_bytes_total": Gauge(
                "skriptoteket_session_files_bytes_total",
                "Total bytes of stored session files",
                registry=registry,
            ),
            "session_files_count": Gauge(
                "skriptoteket_session_files_count",
                "Count of stored session files",
                registry=registry,
            ),
            "logins_total": Counter(
                "skriptoteket_logins_total",
                "Total login attempts",
                ["status"],
                registry=registry,
            ),
        },
    )
    monkeypatch.setattr(observability_routes, "generate_latest", lambda: generate_latest(registry))
    monkeypatch.setattr(
        observability_routes,
        "get_identity_metrics",
        lambda: (_ for _ in ()).throw(AssertionError("identity metrics must stay disabled")),
    )
    production_settings = Settings.model_construct(
        APP_NAME="Skriptoteket",
        APP_VERSION="0.2.0",
        SERVICE_NAME="skriptoteket",
        ENVIRONMENT="production",
        METRICS_IDENTITY_GAUGES_ENABLED=None,
        ARTIFACTS_ROOT=Settings().ARTIFACTS_ROOT,
    )
    app = _build_app(
        settings=production_settings,
        engine=engine,
        users=users,
        clock=clock,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "skriptoteket_session_files_bytes_total" in response.text
    assert "skriptoteket_active_sessions" not in response.text
    assert "skriptoteket_users_by_role" not in response.text
    users.count_active_by_role.assert_not_awaited()


def _build_app(
    *,
    settings: Settings,
    engine: AsyncEngine,
    users: UserRepositoryProtocol,
    clock: ClockProtocol,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(observability_routes.router)

    container = make_async_container(
        ObservabilityProvider(
            settings=settings,
            engine=engine,
            users=users,
            clock=clock,
        )
    )
    setup_dishka(container, app)
    return app
