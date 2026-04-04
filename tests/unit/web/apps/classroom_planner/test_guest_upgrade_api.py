"""Route tests for the authenticated Klassrumskartan guest-upgrade endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerGuestUpgradeHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    SNAPSHOT_PROFILE,
    ClassroomPlannerGuestSnapshotPayload,
    ClassroomPlannerGuestUpgradeReceipt,
    ClassroomPlannerGuestUpgradeRequest,
    GuestUpgradeUiStatePayload,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_guest_upgrade as guest_upgrade_api,
)
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class GuestUpgradeApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: CurrentUserProviderProtocol,
        sessions: SessionRepositoryProtocol,
        guest_upgrade_handler: ClassroomPlannerGuestUpgradeHandler,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._guest_upgrade_handler = guest_upgrade_handler

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
    def guest_upgrade_handler(self) -> ClassroomPlannerGuestUpgradeHandler:
        return self._guest_upgrade_handler


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 4, 12, 0, 0)


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
    repository = AsyncMock(spec=SessionRepositoryProtocol)
    repository.get_by_id.return_value = None
    return repository


@pytest.fixture
def guest_upgrade_handler() -> AsyncMock:
    return AsyncMock(spec=ClassroomPlannerGuestUpgradeHandler)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    guest_upgrade_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(guest_upgrade_api.router)

    container = make_async_container(
        GuestUpgradeApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
            guest_upgrade_handler=guest_upgrade_handler,
        )
    )
    setup_dishka(container, app)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client


def _request_payload() -> ClassroomPlannerGuestUpgradeRequest:
    return ClassroomPlannerGuestUpgradeRequest(
        mode="preview",
        snapshot=ClassroomPlannerGuestSnapshotPayload(
            schema_version=1,
            profile=SNAPSHOT_PROFILE,
            snapshot_id="guest-snapshot-1",
            snapshot_content_hash="sha256:submitted",
            created_at="2026-04-04T12:00:00Z",
            updated_at="2026-04-04T12:00:00Z",
            expires_at="2026-04-18T12:00:00Z",
            ui_state=GuestUpgradeUiStatePayload(
                selected_roster_local_id=None,
                selected_template_local_id=None,
                current_screen="class-workspace",
                planner_initial_view="groups",
                dismissed_grouping_draft_local_id=None,
                dismissed_seating_draft_local_id=None,
                fingerprint="sha256:ui",
            ),
        ),
    )


@pytest.mark.asyncio
async def test_guest_upgrade_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/guest-upgrade",
        json=_request_payload().model_dump(mode="json"),
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guest_upgrade_requires_csrf(
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
        "/api/v1/apps/classroom.group-seating-studio/guest-upgrade",
        json=_request_payload().model_dump(mode="json"),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_guest_upgrade_returns_receipt(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    guest_upgrade_handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)
    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    payload = _request_payload()
    guest_upgrade_handler.handle.return_value = ClassroomPlannerGuestUpgradeReceipt(
        mode="preview",
        snapshot_id=payload.snapshot.snapshot_id,
        schema_version=payload.snapshot.schema_version,
        submitted_snapshot_content_hash=payload.snapshot.snapshot_content_hash,
        server_snapshot_content_hash="sha256:server",
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/guest-upgrade",
        json=payload.model_dump(mode="json"),
        headers={"X-CSRF-Token": session.csrf_token},
    )

    assert response.status_code == 200
    assert response.json()["snapshot_id"] == payload.snapshot.snapshot_id
    guest_upgrade_handler.handle.assert_awaited_once()
    assert guest_upgrade_handler.handle.await_args.kwargs["owner_user_id"] == user.id
    assert guest_upgrade_handler.handle.await_args.kwargs["request"].mode == "preview"
