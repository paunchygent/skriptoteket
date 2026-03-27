"""API tests for the classroom planner smart-seating endpoint."""

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI

from skriptoteket.application.curated_apps.classroom_planner import RunSmartSeatingHandler
from skriptoteket.application.curated_apps.classroom_planner.handlers.smart_seating import (
    SmartSeatingAppliedResult,
    SmartSeatingBlockedResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftHistoryStatus,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
)
from skriptoteket.web.api.v1 import apps_classroom_planner_seating as api
from skriptoteket.web.dishka_compat import setup_dishka
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_session, make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class SmartSeatingApiProvider(Provider):
    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        current_user_provider: CurrentUserProviderProtocol,
        sessions: SessionRepositoryProtocol,
        handler: RunSmartSeatingHandler,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._clock = clock
        self._current_user_provider = current_user_provider
        self._sessions = sessions
        self._handler = handler

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
    def run_smart_seating_handler(self) -> RunSmartSeatingHandler:
        return self._handler


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
def handler() -> AsyncMock:
    return AsyncMock(spec=RunSmartSeatingHandler)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockProtocol,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)

    container = make_async_container(
        SmartSeatingApiProvider(
            settings=settings,
            clock=clock,
            current_user_provider=current_user_provider,
            sessions=sessions,
            handler=handler,
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


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _workspace(*, owner_user_id, roster_id, draft_id=None) -> ClassroomPlannerWorkspace:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=draft_id or uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
            template_id=uuid4(),
            smart_enabled=True,
            use_history=True,
            status=PlanDraftStatus.ACTIVE,
            revision=5,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        roster=Roster(
            id=roster_id,
            owner_user_id=owner_user_id,
            name="SA24D",
            students=[
                Student(id="ada", display_name="Ada"),
                Student(id="alan", display_name="Alan"),
            ],
            created_at=now,
            updated_at=now,
        ),
        template=RoomTemplate(
            id=uuid4(),
            owner_user_id=owner_user_id,
            name="Sal 101",
            grid_cols=4,
            grid_rows=3,
            seats=[
                Seat(id="front-left", x=0, y=0),
                Seat(id="front-right", x=1, y=0),
            ],
            fixtures=[
                RoomFixture(
                    id="board-1",
                    type=RoomFixtureType.WHITEBOARD,
                    x=0,
                    y=0,
                    width=1,
                    height=1,
                )
            ],
            created_at=now,
            updated_at=now,
        ),
        groups=[],
        group_assignments=[],
        seat_assignments=[
            SeatAssignment(student_id="ada", seat_id="front-right"),
            SeatAssignment(student_id="alan", seat_id="front-left"),
        ],
        student_planning_meta=[],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_seating_returns_applied_payload_from_handler() -> None:
    user = make_user(role=Role.USER)
    roster_id = uuid4()
    workspace = _workspace(owner_user_id=user.id, roster_id=roster_id)
    handler = AsyncMock(spec=RunSmartSeatingHandler)
    handler.handle.return_value = SmartSeatingAppliedResult(
        status="applied",
        workspace=workspace,
        used_history=True,
        message="Smart placering klar med stöd av tidigare exporter.",
    )

    result = await _unwrap_dishka(api.run_smart_seating)(
        draft_id=workspace.draft.id,
        request=api.SmartSeatingRunRequest(expected_revision=workspace.draft.revision),
        handler=handler,
        user=user,
    )

    assert result.status == "applied"
    assert result.workspace.draft.id == workspace.draft.id
    assert result.used_history is True
    handler.handle.assert_awaited_once_with(
        draft_id=workspace.draft.id,
        owner_user_id=user.id,
        expected_revision=workspace.draft.revision,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_seating_returns_blocked_payload_for_no_history() -> None:
    user = make_user(role=Role.USER)
    draft_id = uuid4()
    handler = AsyncMock(spec=RunSmartSeatingHandler)
    handler.handle.return_value = SmartSeatingBlockedResult(
        status="blocked",
        reason="no_history",
        message=(
            "För att använda historik behöver du först exportera "
            "ett sittschema för just det här klassrummet."
        ),
        used_history=False,
    )

    result = await _unwrap_dishka(api.run_smart_seating)(
        draft_id=draft_id,
        request=api.SmartSeatingRunRequest(expected_revision=4),
        handler=handler,
        user=user,
    )

    assert result.status == "blocked"
    assert result.reason == "no_history"
    assert result.workspace is None
    assert result.used_history is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_seating_route_returns_not_found_for_missing_draft(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)
    draft_id = uuid4()

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    handler.handle.side_effect = not_found("PlanDraft", str(draft_id))

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/smart-run",
        headers={"X-CSRF-Token": session.csrf_token},
        json={"expected_revision": 4},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.NOT_FOUND.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_seating_route_returns_conflict_for_stale_revision(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)
    draft_id = uuid4()

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session
    handler.handle.side_effect = DomainError(
        code=ErrorCode.CONFLICT,
        message="Draft revision mismatch.",
    )

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/smart-run",
        headers={"X-CSRF-Token": session.csrf_token},
        json={"expected_revision": 4},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == ErrorCode.CONFLICT.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_seating_route_returns_422_for_malformed_payload(
    client: httpx.AsyncClient,
    settings: Settings,
    current_user_provider: AsyncMock,
    sessions: AsyncMock,
    handler: AsyncMock,
    now: datetime,
) -> None:
    user = make_user(role=Role.USER)
    session = make_session(user_id=user.id, now=now)
    draft_id = uuid4()

    current_user_provider.get_current_user.return_value = user
    sessions.get_by_id.return_value = session

    client.cookies.set(settings.SESSION_COOKIE_NAME, str(session.id))
    response = await client.post(
        f"/api/v1/apps/classroom.group-seating-studio/drafts/seating/{draft_id}/smart-run",
        headers={"X-CSRF-Token": session.csrf_token},
        json={},
    )

    assert response.status_code == 422
    handler.handle.assert_not_awaited()
