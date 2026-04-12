"""API tests for the classroom planner smart-grouping endpoint."""

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.classroom_planner import RunSmartGroupingHandler
from skriptoteket.application.curated_apps.classroom_planner.handlers.smart_grouping import (
    SmartGroupingAppliedResult,
    SmartGroupingBlockedResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    DraftHistoryStatus,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    Roster,
    Student,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_classroom_planner_grouping as api
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class SmartGroupingApiProvider(Provider):
    def __init__(
        self,
        *,
        handler: RunSmartGroupingHandler,
    ) -> None:
        super().__init__()
        self._handler = handler

    @provide(scope=Scope.REQUEST)
    def run_smart_grouping_handler(self) -> RunSmartGroupingHandler:
        return self._handler


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
def handler() -> AsyncMock:
    return AsyncMock(spec=RunSmartGroupingHandler)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(api.router)

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        SmartGroupingApiProvider(
            handler=handler,
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


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _workspace(*, owner_user_id, roster_id, draft_id=None) -> ClassroomPlannerWorkspace:
    now = datetime(2026, 3, 29, tzinfo=timezone.utc)
    return ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=draft_id or uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.GROUPING,
            template_id=None,
            smart_enabled=True,
            use_history=True,
            grouping_seating_distance_enabled=True,
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
        template=None,
        groups=[DraftGroup(id="group-1", name="Grupp 1", sort_order=0)],
        group_assignments=[
            GroupAssignment(student_id="ada", group_id="group-1"),
            GroupAssignment(student_id="alan", group_id="group-1"),
        ],
        seat_assignments=[],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_grouping_returns_applied_payload_from_handler() -> None:
    user = make_user(role=Role.USER)
    roster_id = uuid4()
    workspace = _workspace(owner_user_id=user.id, roster_id=roster_id)
    handler = AsyncMock(spec=RunSmartGroupingHandler)
    handler.handle.return_value = SmartGroupingAppliedResult(
        status="applied",
        workspace=workspace,
        used_history=True,
        used_live_seating=True,
        message="Smart gruppindelning klar med historik och aktuell sittning som stöd.",
    )

    result = await _unwrap_dishka(api.run_smart_grouping)(
        draft_id=workspace.draft.id,
        request=api.SmartGroupingRunRequest(expected_revision=workspace.draft.revision),
        handler=handler,
        user=user,
    )

    assert result.status == "applied"
    assert result.workspace.draft.id == workspace.draft.id
    assert result.used_history is True
    assert result.used_live_seating is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_grouping_returns_blocked_payload_for_no_history() -> None:
    user = make_user(role=Role.USER)
    draft_id = uuid4()
    handler = AsyncMock(spec=RunSmartGroupingHandler)
    handler.handle.return_value = SmartGroupingBlockedResult(
        status="blocked",
        reason="no_history",
        message="För att använda historik behöver du först exportera en gruppindelning.",
        used_history=False,
        used_live_seating=True,
    )

    result = await _unwrap_dishka(api.run_smart_grouping)(
        draft_id=draft_id,
        request=api.SmartGroupingRunRequest(expected_revision=4),
        handler=handler,
        user=user,
    )

    assert result.status == "blocked"
    assert result.reason == "no_history"
    assert result.workspace is None
    assert result.used_history is False
    assert result.used_live_seating is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_grouping_route_returns_not_found_for_missing_draft(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)
    draft_id = uuid4()

    handler.handle.side_effect = not_found("PlanDraft", str(draft_id))

    response = await client.post(
        f"/api/v1/apps/classroom.group-seating-studio/drafts/grouping/{draft_id}/smart-run",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"expected_revision": 4},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == ErrorCode.NOT_FOUND.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_smart_grouping_route_returns_conflict_for_stale_revision(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    handler: AsyncMock,
    now: datetime,
) -> None:
    seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)
    draft_id = uuid4()

    handler.handle.side_effect = DomainError(
        code=ErrorCode.CONFLICT,
        message="Draft revision mismatch.",
    )

    response = await client.post(
        f"/api/v1/apps/classroom.group-seating-studio/drafts/grouping/{draft_id}/smart-run",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        json={"expected_revision": 4},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == ErrorCode.CONFLICT.value
