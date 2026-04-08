"""Behavior tests for classroom planner guest-upgrade orchestration."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerGuestUpgradeHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    SNAPSHOT_PROFILE,
    ClassroomPlannerGuestUpgradeRequest,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    PlanDraftKind,
    RelationshipKind,
    RosterSmartRules,
)
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
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from tests.fixtures.application_fixtures import FakeUow


@pytest.fixture
def owner_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def uow() -> FakeUow:
    return FakeUow()


@pytest.fixture
def rosters() -> AsyncMock:
    repository = AsyncMock(spec=RosterRepositoryProtocol)
    repository.list_by_owner.return_value = []
    return repository


@pytest.fixture
def templates() -> AsyncMock:
    repository = AsyncMock(spec=RoomTemplateRepositoryProtocol)
    repository.list_by_owner.return_value = []
    return repository


@pytest.fixture
def smart_rules() -> AsyncMock:
    return AsyncMock(spec=RosterSmartRuleRepositoryProtocol)


@pytest.fixture
def drafts() -> AsyncMock:
    return AsyncMock(spec=PlanDraftRepositoryProtocol)


@pytest.fixture
def seating_checkpoints() -> AsyncMock:
    return AsyncMock(spec=SeatingExportCheckpointRepositoryProtocol)


@pytest.fixture
def grouping_checkpoints() -> AsyncMock:
    return AsyncMock(spec=GroupingExportCheckpointRepositoryProtocol)


@pytest.fixture
def seating_export_jobs() -> AsyncMock:
    return AsyncMock(spec=SeatingExportJobRepositoryProtocol)


@pytest.fixture
def grouping_export_jobs() -> AsyncMock:
    return AsyncMock(spec=GroupingExportJobRepositoryProtocol)


@pytest.fixture
def guest_upgrade_repository() -> AsyncMock:
    repository = AsyncMock(spec=ClassroomPlannerGuestUpgradeRepositoryProtocol)
    repository.get_imported_draft_by_identity.return_value = None
    repository.grouping_checkpoint_exists.return_value = False
    repository.seating_checkpoint_exists.return_value = False
    return repository


@pytest.fixture
def clock(now: datetime) -> Mock:
    mock = Mock(spec=ClockProtocol)
    mock.now.return_value = now
    return mock


def _id_generator(*ids: UUID) -> Mock:
    mock = Mock(spec=IdGeneratorProtocol)
    mock.new_uuid.side_effect = list(ids)
    return mock


def _handler(
    *,
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
    id_generator: Mock,
) -> ClassroomPlannerGuestUpgradeHandler:
    return ClassroomPlannerGuestUpgradeHandler(
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
        id_generator=id_generator,
    )


def _request(
    *,
    mode: str = "commit",
    rosters: list[dict] | None = None,
    templates: list[dict] | None = None,
    smart_rule_sets: list[dict] | None = None,
    grouping_draft: dict | None = None,
    seating_draft: dict | None = None,
    checkpoint_descriptors: list[dict] | None = None,
) -> ClassroomPlannerGuestUpgradeRequest:
    return ClassroomPlannerGuestUpgradeRequest.model_validate(
        {
            "mode": mode,
            "snapshot": {
                "schema_version": 1,
                "profile": SNAPSHOT_PROFILE,
                "snapshot_id": "guest-snapshot-1",
                "snapshot_content_hash": "sha256:client",
                "created_at": "2026-04-04T12:00:00Z",
                "updated_at": "2026-04-04T12:00:00Z",
                "expires_at": "2026-04-18T12:00:00Z",
                "rosters": rosters or [],
                "templates": templates or [],
                "smart_rule_sets": smart_rule_sets or [],
                "grouping_draft": grouping_draft,
                "seating_draft": seating_draft,
                "checkpoint_descriptors": checkpoint_descriptors or [],
                "ui_state": {
                    "selected_roster_local_id": None,
                    "selected_template_local_id": None,
                    "current_screen": "class-workspace",
                    "planner_initial_view": "groups",
                    "dismissed_grouping_draft_local_id": None,
                    "dismissed_seating_draft_local_id": None,
                    "fingerprint": "sha256:ui",
                },
            },
        }
    )


def _guest_roster() -> dict:
    return {
        "local_id": "roster-1",
        "name": "SA24D",
        "students": [
            {"local_id": "student-1", "display_name": "Ada Andersson"},
            {"local_id": "student-2", "display_name": "Bo Berg"},
        ],
        "fingerprint": "sha256:roster",
    }


def _guest_grouping_draft() -> dict:
    return {
        "local_id": "draft-grouping-1",
        "draft_kind": "grouping",
        "roster_local_id": "roster-1",
        "template_local_id": None,
        "task_entry_classroom_selection_mode": "optional",
        "smart_enabled": False,
        "use_history": False,
        "grouping_seating_distance_enabled": False,
        "revision": 4,
        "last_opened_at": "2026-04-04T12:00:00Z",
        "groups": [
            {
                "id": "group-1",
                "name": "Grupp 1",
                "sort_order": 1,
                "name_is_custom": False,
            }
        ],
        "group_assignments": [{"student_id": "student-1", "group_id": "group-1"}],
        "seat_assignments": [],
        "fingerprint": "sha256:draft",
    }


@pytest.mark.asyncio
async def test_guest_upgrade_conflicts_invalid_smart_rules_instead_of_raising(
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
    created_roster_id = uuid4()
    smart_rules.get_by_roster_id.return_value = RosterSmartRules(
        roster_id=created_roster_id,
        revision=0,
        seating_preferences=[],
        relationship_rules=[],
    )
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
        id_generator=_id_generator(created_roster_id),
    )

    receipt = await handler.handle(
        owner_user_id=owner_user_id,
        request=_request(
            rosters=[_guest_roster()],
            smart_rule_sets=[
                {
                    "roster_local_id": "roster-1",
                    "revision": 1,
                    "seating_preferences": [],
                    "relationship_rules": [
                        {
                            "id": "rule-1",
                            "kind": RelationshipKind.KEEP_NEAR.value,
                            "student_ids": ["student-1", "missing-student"],
                        }
                    ],
                    "fingerprint": "sha256:rules",
                }
            ],
        ),
    )

    assert any(
        item.entity_type == "smart_rule_set" and item.local_id == "roster-1"
        for item in receipt.conflicted
    )
    smart_rules.save.assert_not_awaited()
    guest_upgrade_repository.record_upgrade_consumption.assert_awaited_once_with(
        owner_user_id=owner_user_id,
        app_id="classroom.group-seating-studio",
        snapshot_id="guest-snapshot-1",
        consumed_at=clock.now.return_value,
    )


@pytest.mark.asyncio
async def test_guest_upgrade_commit_records_consumption_for_meaningful_import(
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
    created_roster_id = uuid4()
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
        id_generator=_id_generator(created_roster_id),
    )

    receipt = await handler.handle(
        owner_user_id=owner_user_id,
        request=_request(rosters=[_guest_roster()]),
    )

    assert len(receipt.created) == 1
    guest_upgrade_repository.record_upgrade_consumption.assert_awaited_once_with(
        owner_user_id=owner_user_id,
        app_id="classroom.group-seating-studio",
        snapshot_id="guest-snapshot-1",
        consumed_at=clock.now.return_value,
    )


@pytest.mark.asyncio
async def test_guest_upgrade_preview_does_not_record_consumption(
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
    created_roster_id = uuid4()
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
        id_generator=_id_generator(created_roster_id),
    )

    receipt = await handler.handle(
        owner_user_id=owner_user_id,
        request=_request(mode="preview", rosters=[_guest_roster()]),
    )

    assert len(receipt.created) == 1
    guest_upgrade_repository.record_upgrade_consumption.assert_not_awaited()


@pytest.mark.asyncio
async def test_guest_upgrade_rejects_invalid_historical_draft_without_saving(
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
    created_roster_id = uuid4()
    created_draft_id = uuid4()
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
        id_generator=_id_generator(created_roster_id, created_draft_id),
    )

    invalid_grouping_draft = _guest_grouping_draft()
    invalid_grouping_draft["group_assignments"] = [
        {"student_id": "student-1", "group_id": "missing-group"}
    ]

    receipt = await handler.handle(
        owner_user_id=owner_user_id,
        request=_request(
            rosters=[_guest_roster()],
            grouping_draft=invalid_grouping_draft,
        ),
    )

    assert any(
        item.entity_type == "draft"
        and item.local_id == "draft-grouping-1"
        and item.message == "Group assignments must reference existing groups."
        for item in receipt.conflicted
    )
    drafts.save_workspace.assert_not_awaited()


def test_guest_upgrade_rejects_metadata_only_grouping_checkpoint_payload() -> None:
    with pytest.raises(ValidationError) as error:
        _request(
            rosters=[_guest_roster()],
            grouping_draft=_guest_grouping_draft(),
            checkpoint_descriptors=[
                {
                    "local_id": "checkpoint-1",
                    "draft_kind": PlanDraftKind.GROUPING.value,
                    "created_at": "2026-04-04T12:05:00Z",
                    "label": "Metadata-only checkpoint",
                    "source": "export",
                    "fingerprint": "sha256:checkpoint",
                }
            ],
        )

    assert "Grouping checkpoints must include group_assignments." in str(error.value)
