"""Route tests for public Klassrumskartan Smart helpers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.classroom_planner import (
    RunPublicSmartGroupingHandler,
    RunPublicSmartSeatingHandler,
)
from skriptoteket.config import Settings
from skriptoteket.di.infrastructure.services import InfrastructureServicesProvider
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
from skriptoteket.web.api.v1 import public_apps_classroom_planner_smart as public_smart_api
from skriptoteket.web.middleware.error_handler import error_handler_middleware


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class PublicPlannerSmartApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        registry: CuratedAppRegistryProtocol,
        throttle: PublicHelperThrottleProtocol,
        grouping_handler: RunPublicSmartGroupingHandler,
        seating_handler: RunPublicSmartSeatingHandler,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._registry = registry
        self._throttle = throttle
        self._grouping_handler = grouping_handler
        self._seating_handler = seating_handler

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
    def grouping_handler(self) -> RunPublicSmartGroupingHandler:
        return self._grouping_handler

    @provide(scope=Scope.REQUEST)
    def seating_handler(self) -> RunPublicSmartSeatingHandler:
        return self._seating_handler


class PublicPlannerSmartRuntimeProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        registry: CuratedAppRegistryProtocol,
        grouping_handler: RunPublicSmartGroupingHandler,
        seating_handler: RunPublicSmartSeatingHandler,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._registry = registry
        self._grouping_handler = grouping_handler
        self._seating_handler = seating_handler

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return self._clock

    @provide(scope=Scope.APP)
    def registry(self) -> CuratedAppRegistryProtocol:
        return self._registry

    @provide(scope=Scope.REQUEST)
    def grouping_handler(self) -> RunPublicSmartGroupingHandler:
        return self._grouping_handler

    @provide(scope=Scope.REQUEST)
    def seating_handler(self) -> RunPublicSmartSeatingHandler:
        return self._seating_handler


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


def _smart_run_request(*, draft_kind: str) -> dict[str, object]:
    grouping_draft = {
        "local_id": "grouping-draft-1",
        "draft_kind": "grouping",
        "roster_local_id": "roster-1",
        "template_local_id": "template-1",
        "task_entry_classroom_selection_mode": "optional",
        "smart_enabled": True,
        "use_history": False,
        "grouping_seating_distance_enabled": True,
        "revision": 4,
        "last_opened_at": "2026-04-07T10:00:00Z",
        "groups": [
            {"id": "group-a", "name": "Grupp 1", "sort_order": 0, "name_is_custom": False},
            {"id": "group-b", "name": "Grupp 2", "sort_order": 1, "name_is_custom": False},
        ],
        "group_assignments": [
            {"student_id": "ada", "group_id": "group-a"},
            {"student_id": "alan", "group_id": "group-b"},
        ],
        "seat_assignments": [],
        "fingerprint": "sha256:grouping-draft",
    }
    seating_draft = {
        "local_id": "seating-draft-1",
        "draft_kind": "seating",
        "roster_local_id": "roster-1",
        "template_local_id": "template-1",
        "task_entry_classroom_selection_mode": "required",
        "smart_enabled": True,
        "use_history": False,
        "grouping_seating_distance_enabled": False,
        "revision": 2,
        "last_opened_at": "2026-04-07T10:00:00Z",
        "groups": [],
        "group_assignments": [],
        "seat_assignments": [
            {"student_id": "ada", "seat_id": "seat-1"},
            {"student_id": "alan", "seat_id": "seat-2"},
        ],
        "fingerprint": "sha256:seating-draft",
    }
    return {
        "expected_revision": 4 if draft_kind == "grouping" else 2,
        "snapshot": {
            "schema_version": 1,
            "profile": "public_browser_workspace_with_upgrade",
            "snapshot_id": "snapshot-1",
            "snapshot_content_hash": "sha256:snapshot",
            "created_at": "2026-04-07T09:00:00Z",
            "updated_at": "2026-04-07T10:00:00Z",
            "expires_at": "2026-04-21T10:00:00Z",
            "rosters": [
                {
                    "local_id": "roster-1",
                    "name": "SA24D",
                    "students": [
                        {"local_id": "ada", "display_name": "Ada"},
                        {"local_id": "alan", "display_name": "Alan"},
                    ],
                    "fingerprint": "sha256:roster",
                }
            ],
            "templates": [
                {
                    "local_id": "template-1",
                    "name": "Sal 101",
                    "grid_cols": 4,
                    "grid_rows": 4,
                    "seats": [
                        {"id": "seat-1", "x": 0, "y": 0, "zone": None},
                        {"id": "seat-2", "x": 1, "y": 0, "zone": None},
                    ],
                    "fixtures": [],
                    "fingerprint": "sha256:template",
                }
            ],
            "smart_rule_sets": [
                {
                    "roster_local_id": "roster-1",
                    "revision": 1,
                    "seating_preferences": [],
                    "relationship_rules": [],
                    "fingerprint": "sha256:rules",
                }
            ],
            "grouping_draft": grouping_draft,
            "seating_draft": seating_draft,
            "checkpoint_descriptors": [],
            "ui_state": {
                "selected_roster_local_id": "roster-1",
                "selected_template_local_id": "template-1",
                "current_screen": "planner",
                "planner_initial_view": "groups" if draft_kind == "grouping" else "seats",
                "dismissed_grouping_draft_local_id": None,
                "dismissed_seating_draft_local_id": None,
                "fingerprint": "sha256:ui-state",
            },
        },
    }


def _grouping_response() -> dict[str, object]:
    return {
        "status": "applied",
        "workspace": {
            "draft": {
                "id": "grouping-draft-1",
                "roster_id": "roster-1",
                "draft_kind": "grouping",
                "template_id": "template-1",
                "task_entry_classroom_selection_mode": "optional",
                "smart_enabled": True,
                "use_history": False,
                "grouping_seating_distance_enabled": True,
                "status": "active",
                "revision": 5,
                "last_opened_at": "2026-04-07T10:00:00Z",
            },
            "roster": {
                "id": "roster-1",
                "name": "SA24D",
                "students": [
                    {"id": "ada", "display_name": "Ada"},
                    {"id": "alan", "display_name": "Alan"},
                ],
            },
            "template": {
                "id": "template-1",
                "name": "Sal 101",
                "grid_cols": 4,
                "grid_rows": 4,
                "seats": [
                    {"id": "seat-1", "x": 0, "y": 0, "zone": None},
                    {"id": "seat-2", "x": 1, "y": 0, "zone": None},
                ],
                "fixtures": [],
            },
            "groups": [
                {"id": "group-a", "name": "Grupp 1", "sort_order": 0, "name_is_custom": False},
                {"id": "group-b", "name": "Grupp 2", "sort_order": 1, "name_is_custom": False},
            ],
            "group_assignments": [
                {"student_id": "ada", "group_id": "group-b"},
                {"student_id": "alan", "group_id": "group-a"},
            ],
            "seat_assignments": [],
            "history_status": {"can_undo": False, "can_redo": False},
        },
        "used_history": False,
        "used_live_seating": True,
        "message": "Smart gruppindelning klar med stöd från klassens sittschema.",
    }


def _seating_response() -> dict[str, object]:
    return {
        "status": "applied",
        "workspace": {
            "draft": {
                "id": "seating-draft-1",
                "roster_id": "roster-1",
                "draft_kind": "seating",
                "template_id": "template-1",
                "task_entry_classroom_selection_mode": "required",
                "smart_enabled": True,
                "use_history": False,
                "grouping_seating_distance_enabled": False,
                "status": "active",
                "revision": 3,
                "last_opened_at": "2026-04-07T10:00:00Z",
            },
            "roster": {
                "id": "roster-1",
                "name": "SA24D",
                "students": [
                    {"id": "ada", "display_name": "Ada"},
                    {"id": "alan", "display_name": "Alan"},
                ],
            },
            "template": {
                "id": "template-1",
                "name": "Sal 101",
                "grid_cols": 4,
                "grid_rows": 4,
                "seats": [
                    {"id": "seat-1", "x": 0, "y": 0, "zone": None},
                    {"id": "seat-2", "x": 1, "y": 0, "zone": None},
                ],
                "fixtures": [],
            },
            "groups": [],
            "group_assignments": [],
            "seat_assignments": [
                {"student_id": "ada", "seat_id": "seat-2"},
                {"student_id": "alan", "seat_id": "seat-1"},
            ],
            "history_status": {"can_undo": False, "can_redo": False},
        },
        "used_history": False,
        "message": "Smart placering klar.",
    }


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 7, 12, 0, 0)


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
def throttle() -> PublicHelperThrottleProtocol:
    return InMemoryPublicHelperRequestThrottle()


@pytest.fixture
def grouping_handler() -> AsyncMock:
    return AsyncMock(spec=RunPublicSmartGroupingHandler)


@pytest.fixture
def seating_handler() -> AsyncMock:
    return AsyncMock(spec=RunPublicSmartSeatingHandler)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    registry: Mock,
    throttle: PublicHelperThrottleProtocol,
    grouping_handler: AsyncMock,
    seating_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(public_smart_api.router)

    container = make_async_container(
        PublicPlannerSmartApiProvider(
            settings=settings,
            clock=clock,
            registry=registry,
            throttle=throttle,
            grouping_handler=grouping_handler,
            seating_handler=seating_handler,
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
async def test_public_grouping_smart_run_succeeds_without_auth_or_csrf(
    client: httpx.AsyncClient,
    grouping_handler: AsyncMock,
) -> None:
    grouping_handler.handle.return_value = _grouping_response()
    client.cookies.set("ambient_auth_cookie", "ambient-session-cookie")

    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
        json=_smart_run_request(draft_kind="grouping"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    kwargs = grouping_handler.handle.call_args.kwargs
    assert kwargs["expected_revision"] == 4
    assert kwargs["snapshot"].profile == "public_browser_workspace_with_upgrade"


@pytest.mark.asyncio
async def test_public_seating_smart_run_succeeds_without_auth_or_csrf(
    client: httpx.AsyncClient,
    seating_handler: AsyncMock,
) -> None:
    seating_handler.handle.return_value = _seating_response()

    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/seating/smart-run",
        json=_smart_run_request(draft_kind="seating"),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    kwargs = seating_handler.handle.call_args.kwargs
    assert kwargs["expected_revision"] == 2
    assert kwargs["snapshot"].profile == "public_browser_workspace_with_upgrade"


@pytest.mark.asyncio
async def test_public_smart_run_fails_closed_when_registry_marks_app_private(
    client: httpx.AsyncClient,
    registry: Mock,
    grouping_handler: AsyncMock,
) -> None:
    registry.get_by_app_id.return_value = _make_app_definition(
        public_access_profile=CuratedAppPublicAccessProfile.AUTHENTICATED_ONLY
    )

    response = await client.post(
        "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
        json=_smart_run_request(draft_kind="grouping"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    grouping_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_grouping_smart_run_rejects_payloads_above_the_public_cap(
    clock: ClockProtocol,
    registry: Mock,
    grouping_handler: AsyncMock,
    seating_handler: AsyncMock,
) -> None:
    settings = Settings(PUBLIC_HELPER_SMART_RUN_MAX_REQUEST_BYTES=32)
    throttle = InMemoryPublicHelperRequestThrottle()
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(public_smart_api.router)
    container = make_async_container(
        PublicPlannerSmartApiProvider(
            settings=settings,
            clock=clock,
            registry=registry,
            throttle=throttle,
            grouping_handler=grouping_handler,
            seating_handler=seating_handler,
        )
    )
    setup_dishka(container, app)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
            content=json.dumps(_smart_run_request(draft_kind="grouping")).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["details"]["reason_code"] == "public_helper_payload_too_large"
    grouping_handler.handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_smart_run_honors_dedicated_smart_rate_limit_in_real_di_provider(
    clock: ClockProtocol,
    registry: Mock,
    grouping_handler: AsyncMock,
    seating_handler: AsyncMock,
) -> None:
    settings = Settings(
        PUBLIC_HELPER_RATE_LIMIT_MAX_REQUESTS=1,
        PUBLIC_HELPER_RATE_LIMIT_WINDOW_SECONDS=60,
        PUBLIC_HELPER_SMART_RUN_MAX_REQUESTS=2,
        PUBLIC_HELPER_SMART_RUN_WINDOW_SECONDS=60,
    )
    grouping_handler.handle.return_value = _grouping_response()

    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(public_smart_api.router)
    container = make_async_container(
        PublicPlannerSmartRuntimeProvider(
            settings=settings,
            clock=clock,
            registry=registry,
            grouping_handler=grouping_handler,
            seating_handler=seating_handler,
        ),
        InfrastructureServicesProvider(),
    )
    setup_dishka(container, app)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        first_response = await client.post(
            "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
            json=_smart_run_request(draft_kind="grouping"),
        )
        second_response = await client.post(
            "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
            json=_smart_run_request(draft_kind="grouping"),
        )
        third_response = await client.post(
            "/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run",
            json=_smart_run_request(draft_kind="grouping"),
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 429
    payload = third_response.json()
    assert payload["error"]["details"]["max_requests"] == 2
    assert payload["error"]["details"]["window_seconds"] == 60
