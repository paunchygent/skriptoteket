"""Route tests for public Klassrumskartan import preview helpers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock, Mock
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
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppPublicAccessProfile,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.security.public_helper_request_throttle import (
    InMemoryPublicHelperRequestThrottle,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_helpers import PublicHelperThrottleProtocol
from skriptoteket.web.api.v1 import public_apps_classroom_planner as public_planner_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class PublicPlannerImportsApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        registry: CuratedAppRegistryProtocol,
        throttle: PublicHelperThrottleProtocol,
        import_handler: CreateClassListImportPreviewHandler,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._registry = registry
        self._throttle = throttle
        self._import_handler = import_handler

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.APP)
    def registry(self) -> CuratedAppRegistryProtocol:
        return self._registry

    @provide(scope=Scope.APP)
    def throttle(self) -> PublicHelperThrottleProtocol:
        return self._throttle

    @provide(scope=Scope.REQUEST)
    def import_handler(self) -> CreateClassListImportPreviewHandler:
        return self._import_handler


def _make_app_definition(
    *,
    public_access_profile: CuratedAppPublicAccessProfile = (
        CuratedAppPublicAccessProfile.PUBLIC_BROWSER_WORKSPACE_WITH_UPGRADE
    ),
) -> CuratedAppDefinition:
    app_id = "classroom.group-seating-studio"
    return CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Klassrumskartan",
        summary="Skapa sittplatsscheman och grupper automatiskt.",
        min_role=Role.USER,
        public_access_profile=public_access_profile,
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
    )


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 3, 12, 0, 0)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def clock(now: datetime) -> ClockProtocol:
    return FixedClock(now=now)


@pytest.fixture
def registry() -> Mock:
    registry = Mock(spec=CuratedAppRegistryProtocol)
    registry.get_by_app_id.return_value = _make_app_definition()
    return registry


@pytest.fixture
def throttle(settings: Settings) -> PublicHelperThrottleProtocol:
    return InMemoryPublicHelperRequestThrottle(
        max_requests=settings.PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS,
    )


@pytest.fixture
def import_handler() -> AsyncMock:
    return AsyncMock(spec=CreateClassListImportPreviewHandler)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    registry: Mock,
    throttle: PublicHelperThrottleProtocol,
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
    app.include_router(public_planner_api.router)

    container = make_async_container(
        PublicPlannerImportsApiProvider(
            settings=settings,
            clock=clock,
            registry=registry,
            throttle=throttle,
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
async def test_public_import_preview_succeeds_without_auth_or_csrf(
    client: httpx.AsyncClient,
    import_handler: AsyncMock,
) -> None:
    import_handler.handle.return_value = ClassListImportPreview(
        file_name="test_class.txt",
        suggested_class_name="SA24D",
        parsed_students=[ParsedStudentRow(full_name="Alice Andersson", row_number=1)],
        ambiguous_rows=[],
    )

    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
        files={"file": ("test_class.txt", b"1. Alice Andersson", "text/plain")},
        headers={"X-Correlation-ID": "53f6d262-789c-4af4-a2c2-5ff5044d452f"},
    )

    assert response.status_code == 200
    assert response.json()["suggested_class_name"] == "SA24D"
    kwargs = import_handler.handle.call_args.kwargs
    assert kwargs["correlation_id"] == "53f6d262-789c-4af4-a2c2-5ff5044d452f"


@pytest.mark.asyncio
async def test_public_import_preview_ignores_ambient_session_cookie(
    client: httpx.AsyncClient,
    import_handler: AsyncMock,
) -> None:
    import_handler.handle.return_value = ClassListImportPreview(
        file_name="test_class.txt",
        suggested_class_name=None,
        parsed_students=[],
        ambiguous_rows=[],
    )

    client.cookies.set("skriptoteket_session", "ambient-session-cookie")
    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
        files={"file": ("test_class.txt", b"class list", "text/plain")},
    )

    assert response.status_code == 200
    import_handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_public_import_preview_fails_closed_when_registry_marks_app_private(
    client: httpx.AsyncClient,
    registry: Mock,
    import_handler: AsyncMock,
) -> None:
    registry.get_by_app_id.return_value = _make_app_definition(
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY
    )

    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
        files={"file": ("test_class.txt", b"class list", "text/plain")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    import_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_import_preview_rejects_unsupported_content_type(
    client: httpx.AsyncClient,
    import_handler: AsyncMock,
) -> None:
    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
        files={"file": ("test_class.txt", b"class list", "image/png")},
    )

    assert response.status_code == 415
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert payload["error"]["details"]["reason_code"] == "public_helper_unsupported_content_type"
    import_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_import_preview_rejects_missing_filename(
    client: httpx.AsyncClient,
    import_handler: AsyncMock,
) -> None:
    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
        files={"file": ("   ", b"class list", "text/plain")},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["details"]["reason_code"] == "public_helper_missing_filename"
    import_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_import_preview_rejects_unsupported_file_suffix(
    client: httpx.AsyncClient,
    import_handler: AsyncMock,
) -> None:
    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
        files={"file": ("class-list.json", b"[]", "application/octet-stream")},
    )

    assert response.status_code == 415
    payload = response.json()
    assert payload["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert payload["error"]["details"]["reason_code"] == "public_helper_unsupported_file_type"
    import_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_import_preview_rejects_payloads_above_the_public_cap(
    clock: ClockProtocol,
    registry: Mock,
    import_handler: AsyncMock,
) -> None:
    settings = Settings(PUBLIC_HELPER_IMPORT_PREVIEW_MAX_FILE_BYTES=4)
    throttle = InMemoryPublicHelperRequestThrottle(
        max_requests=settings.PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS,
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(public_planner_api.router)
    container = make_async_container(
        PublicPlannerImportsApiProvider(
            settings=settings,
            clock=clock,
            registry=registry,
            throttle=throttle,
            import_handler=import_handler,
        )
    )
    setup_dishka(container, app)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
            files={"file": ("test_class.txt", b"12345", "text/plain")},
        )

    assert response.status_code == 413
    assert response.json()["error"]["details"]["reason_code"] == "public_helper_payload_too_large"
    import_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_import_preview_returns_429_when_anonymous_limit_is_exhausted(
    clock: ClockProtocol,
    registry: Mock,
    import_handler: AsyncMock,
) -> None:
    settings = Settings(PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS=1)
    throttle = InMemoryPublicHelperRequestThrottle(
        max_requests=settings.PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS,
    )
    import_handler.handle.return_value = ClassListImportPreview(
        file_name="test_class.txt",
        suggested_class_name=None,
        parsed_students=[],
        ambiguous_rows=[],
    )
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(public_planner_api.router)
    container = make_async_container(
        PublicPlannerImportsApiProvider(
            settings=settings,
            clock=clock,
            registry=registry,
            throttle=throttle,
            import_handler=import_handler,
        )
    )
    setup_dishka(container, app)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        first_response = await client.post(
            "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
            files={"file": ("test_class.txt", b"class list", "text/plain")},
        )
        second_response = await client.post(
            "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
            files={"file": ("test_class.txt", b"class list", "text/plain")},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["error"]["details"]["reason_code"] == "public_helper_rate_limited"


@pytest.mark.asyncio
async def test_public_import_preview_returns_structured_timeout_reason(
    clock: ClockProtocol,
    registry: AsyncMock,
) -> None:
    settings = Settings(PUBLIC_HELPER_IMPORT_PREVIEW_TIMEOUT_SECONDS=0)
    throttle = InMemoryPublicHelperRequestThrottle(
        max_requests=settings.PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS,
    )
    import_handler = AsyncMock(spec=CreateClassListImportPreviewHandler)

    async def _slow_handle(**_: object) -> ClassListImportPreview:
        await asyncio.sleep(0.01)
        return ClassListImportPreview(
            file_name="test_class.txt",
            suggested_class_name=None,
            parsed_students=[],
            ambiguous_rows=[],
        )

    import_handler.handle.side_effect = _slow_handle

    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(public_planner_api.router)
    container = make_async_container(
        PublicPlannerImportsApiProvider(
            settings=settings,
            clock=clock,
            registry=registry,
            throttle=throttle,
            import_handler=import_handler,
        )
    )
    setup_dishka(container, app)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview",
            files={"file": ("test_class.txt", b"class list", "text/plain")},
        )

    assert response.status_code == 503
    assert response.json()["error"]["details"]["reason_code"] == (
        "public_helper_time_budget_exceeded"
    )
