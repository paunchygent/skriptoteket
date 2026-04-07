"""Template-reuse regression tests for classroom planner guest-upgrade flows."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    PlanDraftKind,
    RoomTemplate,
    Seat,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.apps.classroom_planner.test_guest_upgrade_handler import (
    _guest_roster,
    _handler,
    _id_generator,
    _request,
)


@pytest.fixture
def owner_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def uow() -> FakeUow:
    return FakeUow()


@pytest.fixture
def rosters() -> AsyncMock:
    repository = AsyncMock()
    repository.list_by_owner.return_value = []
    return repository


@pytest.fixture
def templates() -> AsyncMock:
    repository = AsyncMock()
    repository.list_by_owner.return_value = []
    return repository


@pytest.fixture
def smart_rules() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def drafts() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def seating_checkpoints() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def grouping_checkpoints() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def seating_export_jobs() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def grouping_export_jobs() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def guest_upgrade_repository() -> AsyncMock:
    repository = AsyncMock()
    repository.get_imported_draft_by_identity.return_value = None
    repository.grouping_checkpoint_exists.return_value = False
    repository.seating_checkpoint_exists.return_value = False
    return repository


@pytest.fixture
def clock() -> Mock:
    mock = Mock()
    mock.now.return_value = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)
    return mock


def _guest_template() -> dict:
    return {
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


def _guest_seating_draft() -> dict:
    return {
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
    }


def _guest_seating_checkpoint() -> dict:
    return {
        "local_id": "checkpoint-seating-1",
        "draft_kind": PlanDraftKind.SEATING.value,
        "created_at": "2026-04-04T12:05:00Z",
        "label": "Export 1",
        "source": "export",
        "template_local_id": "template-1",
        "seat_assignments": [
            {"student_id": "student-1", "seat_id": "guest-seat-1"},
            {"student_id": "student-2", "seat_id": "guest-seat-2"},
        ],
        "fingerprint": "sha256:checkpoint-seating",
    }


@pytest.mark.asyncio
async def test_guest_upgrade_preview_does_not_reuse_unrelated_template_geometry(
    owner_user_id: UUID,
    uow: FakeUow,
    rosters: AsyncMock,
    templates: AsyncMock,
    smart_rules: AsyncMock,
    drafts: AsyncMock,
    seating_checkpoints: AsyncMock,
    grouping_checkpoints: AsyncMock,
    seating_export_jobs: AsyncMock,
    grouping_export_jobs: AsyncMock,
    guest_upgrade_repository: AsyncMock,
    clock: Mock,
) -> None:
    templates.list_by_owner.return_value = [
        RoomTemplate(
            id=uuid4(),
            owner_user_id=owner_user_id,
            name="Annan sal",
            grid_cols=10,
            grid_rows=8,
            seats=[Seat(id="server-seat-x", x=9, y=9, zone=None)],
            fixtures=[],
            created_at=clock.now.return_value,
            updated_at=clock.now.return_value,
        )
    ]
    handler = _handler(
        uow=uow,
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
        id_generator=_id_generator(),
    )

    receipt = await handler.handle(
        owner_user_id=owner_user_id,
        request=_request(
            mode="preview",
            rosters=[_guest_roster()],
            templates=[_guest_template()],
            seating_draft=_guest_seating_draft(),
        ),
    )

    assert any(
        item.entity_type == "template" and item.local_id == "template-1" for item in receipt.created
    )
    assert not any(
        item.entity_type == "template" and item.local_id == "template-1" for item in receipt.reused
    )
    assert not receipt.conflicted


@pytest.mark.asyncio
async def test_guest_upgrade_commit_reuses_matching_template_and_remaps_seating_state(
    owner_user_id: UUID,
    uow: FakeUow,
    rosters: AsyncMock,
    templates: AsyncMock,
    smart_rules: AsyncMock,
    drafts: AsyncMock,
    seating_checkpoints: AsyncMock,
    grouping_checkpoints: AsyncMock,
    seating_export_jobs: AsyncMock,
    grouping_export_jobs: AsyncMock,
    guest_upgrade_repository: AsyncMock,
    clock: Mock,
) -> None:
    existing_template = RoomTemplate(
        id=uuid4(),
        owner_user_id=owner_user_id,
        name="G20",
        grid_cols=14,
        grid_rows=9,
        seats=[
            Seat(id="server-seat-1", x=1, y=1, zone=None),
            Seat(id="server-seat-2", x=2, y=1, zone=None),
        ],
        fixtures=[],
        created_at=clock.now.return_value,
        updated_at=clock.now.return_value,
    )
    templates.list_by_owner.return_value = [existing_template]
    saved_workspaces = []
    created_checkpoints = []

    async def _save_workspace(*, workspace):
        saved_workspaces.append(workspace)

    async def _create_checkpoint(*, checkpoint):
        created_checkpoints.append(checkpoint)
        return checkpoint

    drafts.save_workspace.side_effect = _save_workspace
    seating_checkpoints.create.side_effect = _create_checkpoint

    handler = _handler(
        uow=uow,
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
        id_generator=_id_generator(uuid4(), uuid4(), uuid4(), uuid4()),
    )

    receipt = await handler.handle(
        owner_user_id=owner_user_id,
        request=_request(
            mode="commit",
            rosters=[_guest_roster()],
            templates=[_guest_template()],
            seating_draft=_guest_seating_draft(),
            checkpoint_descriptors=[_guest_seating_checkpoint()],
        ),
    )

    assert any(
        item.entity_type == "template"
        and item.local_id == "template-1"
        and item.target_id == str(existing_template.id)
        for item in receipt.reused
    )
    assert saved_workspaces
    saved_workspace = saved_workspaces[0]
    assert [assignment.seat_id for assignment in saved_workspace.seat_assignments] == [
        "server-seat-1",
        "server-seat-2",
    ]
    assert seating_checkpoints.create.await_count == 1
    assert created_checkpoints[0].template_id == existing_template.id
    assert not receipt.conflicted
