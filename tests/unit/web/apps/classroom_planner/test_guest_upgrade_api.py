"""Route tests for the authenticated Klassrumskartan guest-upgrade endpoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dishka import Provider, Scope, make_async_container, provide
from fastapi import FastAPI
from starlette_dishka import setup_dishka

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerGuestUpgradeHandler,
    GetClassroomPlannerGuestUpgradeConsumptionHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    SNAPSHOT_PROFILE,
    ClassroomPlannerGuestSnapshotPayload,
    ClassroomPlannerGuestUpgradeReceipt,
    ClassroomPlannerGuestUpgradeRequest,
    GuestUpgradeUiStatePayload,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate, Seat
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
    RosterSmartRuleRepositoryProtocol,
    SeatingExportCheckpointRepositoryProtocol,
)
from skriptoteket.protocols.classroom_planner_exports import (
    GroupingExportJobRepositoryProtocol,
    SeatingExportJobRepositoryProtocol,
)
from skriptoteket.protocols.classroom_planner_guest_upgrade import (
    ClassroomPlannerGuestUpgradeRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_guest_upgrade as guest_upgrade_api,
)
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.profile_app_continuation_support import (
    ClockStub,
    ProfileContinuationApiProvider,
    ProfileRepositoryStub,
    UserRepositoryStub,
    seed_huleedu_projection,
    signed_huleedu_headers,
)


class GuestUpgradeApiProvider(Provider):
    def __init__(
        self,
        *,
        guest_upgrade_handler: ClassroomPlannerGuestUpgradeHandler,
        guest_upgrade_consumption_handler: GetClassroomPlannerGuestUpgradeConsumptionHandler,
    ) -> None:
        super().__init__()
        self._guest_upgrade_handler = guest_upgrade_handler
        self._guest_upgrade_consumption_handler = guest_upgrade_consumption_handler

    @provide(scope=Scope.REQUEST)
    def guest_upgrade_handler(self) -> ClassroomPlannerGuestUpgradeHandler:
        return self._guest_upgrade_handler

    @provide(scope=Scope.REQUEST)
    def guest_upgrade_consumption_handler(
        self,
    ) -> GetClassroomPlannerGuestUpgradeConsumptionHandler:
        return self._guest_upgrade_consumption_handler


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 4, 12, 0, 0)


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
def guest_upgrade_handler() -> AsyncMock:
    return AsyncMock(spec=ClassroomPlannerGuestUpgradeHandler)


@pytest.fixture
def guest_upgrade_consumption_handler() -> AsyncMock:
    return AsyncMock(spec=GetClassroomPlannerGuestUpgradeConsumptionHandler)


@pytest.fixture
def app(
    settings: Settings,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    guest_upgrade_handler: AsyncMock,
    guest_upgrade_consumption_handler: AsyncMock,
) -> FastAPI:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(guest_upgrade_api.router)

    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        GuestUpgradeApiProvider(
            guest_upgrade_handler=guest_upgrade_handler,
            guest_upgrade_consumption_handler=guest_upgrade_consumption_handler,
        ),
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


def _template_bearing_request_payload() -> ClassroomPlannerGuestUpgradeRequest:
    return ClassroomPlannerGuestUpgradeRequest.model_validate(
        {
            "mode": "preview",
            "snapshot": {
                "schema_version": 1,
                "profile": SNAPSHOT_PROFILE,
                "snapshot_id": "guest-snapshot-template",
                "snapshot_content_hash": "sha256:submitted",
                "created_at": "2026-04-04T12:00:00Z",
                "updated_at": "2026-04-04T12:00:00Z",
                "expires_at": "2026-04-18T12:00:00Z",
                "rosters": [
                    {
                        "local_id": "roster-1",
                        "name": "SA24D",
                        "students": [
                            {"local_id": "student-1", "display_name": "Ada Andersson"},
                            {"local_id": "student-2", "display_name": "Bo Berg"},
                        ],
                        "fingerprint": "sha256:roster",
                    }
                ],
                "templates": [
                    {
                        "local_id": "template-1",
                        "name": "G20",
                        "grid_cols": 14,
                        "grid_rows": 9,
                        "seats": [
                            {"id": "guest-seat-1", "x": 1, "y": 1, "zone": None},
                            {"id": "guest-seat-2", "x": 2, "y": 1, "zone": None},
                        ],
                        "fixtures": [],
                        "fingerprint": "sha256:template",
                    }
                ],
                "smart_rule_sets": [],
                "grouping_draft": None,
                "seating_draft": {
                    "local_id": "draft-seating-1",
                    "draft_kind": "seating",
                    "roster_local_id": "roster-1",
                    "template_local_id": "template-1",
                    "task_entry_classroom_selection_mode": "required",
                    "smart_enabled": False,
                    "use_history": False,
                    "grouping_seating_distance_enabled": False,
                    "revision": 2,
                    "last_opened_at": "2026-04-04T12:00:00Z",
                    "groups": [],
                    "group_assignments": [],
                    "seat_assignments": [
                        {"student_id": "student-1", "seat_id": "guest-seat-1"},
                        {"student_id": "student-2", "seat_id": "guest-seat-2"},
                    ],
                    "fingerprint": "sha256:seating-draft",
                },
                "checkpoint_descriptors": [],
                "ui_state": {
                    "selected_roster_local_id": "roster-1",
                    "selected_template_local_id": "template-1",
                    "current_screen": "planner",
                    "planner_initial_view": "seats",
                    "dismissed_grouping_draft_local_id": None,
                    "dismissed_seating_draft_local_id": None,
                    "fingerprint": "sha256:ui",
                },
            },
        }
    )


@pytest.mark.asyncio
async def test_guest_upgrade_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/guest-upgrade",
        json=_request_payload().model_dump(mode="json"),
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guest_upgrade_consumption_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/api/v1/apps/classroom.group-seating-studio/guest-upgrade/consumption",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guest_upgrade_rejects_stale_csrf_without_signed_context(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/guest-upgrade",
        json=_request_payload().model_dump(mode="json"),
        headers={"X-CSRF-Token": "stale-local-csrf"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guest_upgrade_returns_receipt(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    guest_upgrade_handler: AsyncMock,
    now: datetime,
) -> None:
    user = seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)
    payload = _request_payload()
    guest_upgrade_handler.handle.return_value = ClassroomPlannerGuestUpgradeReceipt(
        mode="preview",
        snapshot_id=payload.snapshot.snapshot_id,
        schema_version=payload.snapshot.schema_version,
        submitted_snapshot_content_hash=payload.snapshot.snapshot_content_hash,
        server_snapshot_content_hash="sha256:server",
    )

    response = await client.post(
        "/api/v1/apps/classroom.group-seating-studio/guest-upgrade",
        json=payload.model_dump(mode="json"),
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    assert response.json()["snapshot_id"] == payload.snapshot.snapshot_id
    guest_upgrade_handler.handle.assert_awaited_once()
    assert guest_upgrade_handler.handle.await_args.kwargs["owner_user_id"] == user.id
    assert guest_upgrade_handler.handle.await_args.kwargs["request"].mode == "preview"


@pytest.mark.asyncio
async def test_guest_upgrade_consumption_status_returns_backend_truth(
    client: httpx.AsyncClient,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    guest_upgrade_consumption_handler: AsyncMock,
    now: datetime,
) -> None:
    user = seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)
    guest_upgrade_consumption_handler.handle.return_value = True

    response = await client.get(
        "/api/v1/apps/classroom.group-seating-studio/guest-upgrade/consumption",
        headers=signed_huleedu_headers(private_key=private_key, clock=clock),
    )

    assert response.status_code == 200
    assert response.json() == {"consumed": True}
    guest_upgrade_consumption_handler.handle.assert_awaited_once_with(owner_user_id=user.id)


@pytest.mark.asyncio
async def test_guest_upgrade_preview_handles_template_bearing_snapshot_without_500(
    settings: Settings,
    private_key: rsa.RSAPrivateKey,
    clock: ClockStub,
    users: UserRepositoryStub,
    profiles: ProfileRepositoryStub,
    now: datetime,
) -> None:
    user = seed_huleedu_projection(users=users, profiles=profiles, role=Role.USER, now=now)

    rosters = AsyncMock(spec=RosterRepositoryProtocol)
    rosters.list_by_owner.return_value = []
    templates = AsyncMock(spec=RoomTemplateRepositoryProtocol)
    templates.list_by_owner.return_value = [
        RoomTemplate(
            id=uuid4(),
            owner_user_id=user.id,
            name="Annan sal",
            grid_cols=10,
            grid_rows=8,
            seats=[Seat(id="server-seat-x", x=9, y=9, zone=None)],
            fixtures=[],
            created_at=now,
            updated_at=now,
        )
    ]
    smart_rules = AsyncMock(spec=RosterSmartRuleRepositoryProtocol)
    drafts = AsyncMock(spec=PlanDraftRepositoryProtocol)
    seating_checkpoints = AsyncMock(spec=SeatingExportCheckpointRepositoryProtocol)
    grouping_checkpoints = AsyncMock(spec=GroupingExportCheckpointRepositoryProtocol)
    seating_export_jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    grouping_export_jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)
    guest_upgrade_repository = AsyncMock(spec=ClassroomPlannerGuestUpgradeRepositoryProtocol)
    guest_upgrade_repository.get_imported_draft_by_identity.return_value = None
    guest_upgrade_repository.grouping_checkpoint_exists.return_value = False
    guest_upgrade_repository.seating_checkpoint_exists.return_value = False
    id_generator = Mock(spec=IdGeneratorProtocol)

    real_handler = ClassroomPlannerGuestUpgradeHandler(
        uow=FakeUow(),
        rosters=rosters,
        templates=templates,
        smart_rules=smart_rules,
        drafts=drafts,
        seating_checkpoints=seating_checkpoints,
        grouping_checkpoints=grouping_checkpoints,
        seating_export_jobs=seating_export_jobs,
        grouping_export_jobs=grouping_export_jobs,
        guest_upgrade_repository=guest_upgrade_repository,
        clock=clock,
        id_generator=id_generator,
    )

    app = FastAPI()
    app.middleware("http")(error_handler_middleware)
    app.include_router(guest_upgrade_api.router)
    container = make_async_container(
        ProfileContinuationApiProvider(
            settings=settings,
            clock=clock,
            users=users,
            profiles=profiles,
        ),
        GuestUpgradeApiProvider(
            guest_upgrade_handler=real_handler,
            guest_upgrade_consumption_handler=AsyncMock(
                spec=GetClassroomPlannerGuestUpgradeConsumptionHandler
            ),
        ),
    )
    setup_dishka(container, app)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/apps/classroom.group-seating-studio/guest-upgrade",
            json=_template_bearing_request_payload().model_dump(mode="json"),
            headers=signed_huleedu_headers(private_key=private_key, clock=clock),
        )

    assert response.status_code == 200
    assert any(
        item["entity_type"] == "template" and item["local_id"] == "template-1"
        for item in response.json()["created"]
    )
