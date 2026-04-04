"""Behavior tests for guest-upgrade repeat-commit idempotency.

Purpose:
    Prove that authenticated guest-upgrade commit reuses imported historical
    drafts and export-backed checkpoints on repeat submission.
Relationships:
    - Exercises `ClassroomPlannerGuestUpgradeHandler`.
    - Simulates persistence through protocol-scoped stateful mocks instead of
      implementation-detail patching.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerGuestUpgradeHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    SNAPSHOT_PROFILE,
    ClassroomPlannerGuestUpgradeReceipt,
    ClassroomPlannerGuestUpgradeRequest,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    PlanDraft,
    PlanDraftKind,
    Roster,
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


def _request(
    *,
    submitted_snapshot_content_hash: str,
    roster_fingerprint: str,
    draft_fingerprint: str,
    checkpoint_fingerprint: str,
    ui_fingerprint: str,
) -> ClassroomPlannerGuestUpgradeRequest:
    return ClassroomPlannerGuestUpgradeRequest.model_validate(
        {
            "mode": "commit",
            "snapshot": {
                "schema_version": 1,
                "profile": SNAPSHOT_PROFILE,
                "snapshot_id": "guest-snapshot-1",
                "snapshot_content_hash": submitted_snapshot_content_hash,
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
                        "fingerprint": roster_fingerprint,
                    }
                ],
                "templates": [],
                "smart_rule_sets": [],
                "grouping_draft": {
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
                    "fingerprint": draft_fingerprint,
                },
                "seating_draft": None,
                "checkpoint_descriptors": [
                    {
                        "local_id": "checkpoint-1",
                        "draft_kind": PlanDraftKind.GROUPING.value,
                        "created_at": "2026-04-04T12:05:00Z",
                        "label": "Export 1",
                        "source": "export",
                        "group_assignments": [{"student_id": "student-1", "group_id": "group-1"}],
                        "fingerprint": checkpoint_fingerprint,
                    }
                ],
                "ui_state": {
                    "selected_roster_local_id": None,
                    "selected_template_local_id": None,
                    "current_screen": "class-workspace",
                    "planner_initial_view": "groups",
                    "dismissed_grouping_draft_local_id": None,
                    "dismissed_seating_draft_local_id": None,
                    "fingerprint": ui_fingerprint,
                },
            },
        }
    )


def _find_receipt_item(
    receipt: ClassroomPlannerGuestUpgradeReceipt,
    *,
    bucket: str,
    entity_type: str,
    local_id: str,
):
    items = getattr(receipt, bucket)
    return next(
        (item for item in items if item.entity_type == entity_type and item.local_id == local_id),
        None,
    )


@pytest.mark.asyncio
async def test_guest_upgrade_repeat_commit_reuses_historical_grouping_draft_and_checkpoint() -> (
    None
):
    owner_user_id = uuid4()
    created_roster_id = uuid4()
    created_draft_id = uuid4()
    created_grouping_export_job_id = uuid4()
    created_grouping_checkpoint_id = uuid4()
    now = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)
    uow = FakeUow()

    persisted_rosters: list[Roster] = []
    imported_drafts_by_identity: dict[str, PlanDraft] = {}
    imported_grouping_checkpoint_keys: set[tuple[UUID, str]] = set()
    draft_identity_queries: list[str] = []

    rosters = AsyncMock(spec=RosterRepositoryProtocol)

    async def _list_rosters(*, owner_user_id: UUID):
        del owner_user_id
        return list(persisted_rosters)

    async def _save_roster(*, roster):
        persisted_rosters.append(roster)

    rosters.list_by_owner.side_effect = _list_rosters
    rosters.save.side_effect = _save_roster

    templates = AsyncMock(spec=RoomTemplateRepositoryProtocol)
    templates.list_by_owner.return_value = []

    smart_rules = AsyncMock(spec=RosterSmartRuleRepositoryProtocol)

    drafts = AsyncMock(spec=PlanDraftRepositoryProtocol)

    async def _save_workspace(*, workspace):
        imported_drafts_by_identity[workspace.draft.guest_import_identity or ""] = workspace.draft

    drafts.save_workspace.side_effect = _save_workspace

    seating_checkpoints = AsyncMock(spec=SeatingExportCheckpointRepositoryProtocol)
    grouping_checkpoints = AsyncMock(spec=GroupingExportCheckpointRepositoryProtocol)

    async def _create_grouping_checkpoint(*, checkpoint):
        imported_grouping_checkpoint_keys.add((checkpoint.roster_id, checkpoint.assignment_hash))

    grouping_checkpoints.create.side_effect = _create_grouping_checkpoint

    seating_export_jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    grouping_export_jobs = AsyncMock(spec=GroupingExportJobRepositoryProtocol)

    guest_upgrade_repository = AsyncMock(spec=ClassroomPlannerGuestUpgradeRepositoryProtocol)

    async def _get_imported_draft_by_identity(*, owner_user_id: UUID, guest_import_identity: str):
        del owner_user_id
        draft_identity_queries.append(guest_import_identity)
        return imported_drafts_by_identity.get(guest_import_identity)

    async def _grouping_checkpoint_exists(*, roster_id: UUID, assignment_hash: str):
        return (roster_id, assignment_hash) in imported_grouping_checkpoint_keys

    guest_upgrade_repository.get_imported_draft_by_identity.side_effect = (
        _get_imported_draft_by_identity
    )
    guest_upgrade_repository.grouping_checkpoint_exists.side_effect = _grouping_checkpoint_exists
    guest_upgrade_repository.seating_checkpoint_exists.return_value = False

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [
        created_roster_id,
        created_draft_id,
        created_grouping_export_job_id,
        created_grouping_checkpoint_id,
    ]

    handler = ClassroomPlannerGuestUpgradeHandler(
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

    first_receipt = await handler.handle(
        owner_user_id=owner_user_id,
        request=_request(
            submitted_snapshot_content_hash="sha256:submitted-first",
            roster_fingerprint="sha256:client-roster-first",
            draft_fingerprint="sha256:client-draft-first",
            checkpoint_fingerprint="sha256:client-checkpoint-first",
            ui_fingerprint="sha256:client-ui-first",
        ),
    )
    second_receipt = await handler.handle(
        owner_user_id=owner_user_id,
        request=_request(
            submitted_snapshot_content_hash="sha256:submitted-second",
            roster_fingerprint="sha256:client-roster-second",
            draft_fingerprint="sha256:client-draft-second",
            checkpoint_fingerprint="sha256:client-checkpoint-second",
            ui_fingerprint="sha256:client-ui-second",
        ),
    )

    assert first_receipt.submitted_snapshot_content_hash == "sha256:submitted-first"
    assert second_receipt.submitted_snapshot_content_hash == "sha256:submitted-second"
    assert first_receipt.server_snapshot_content_hash == second_receipt.server_snapshot_content_hash
    assert len(set(draft_identity_queries)) == 1

    assert _find_receipt_item(
        first_receipt, bucket="created", entity_type="roster", local_id="roster-1"
    )
    first_draft_item = _find_receipt_item(
        first_receipt, bucket="created", entity_type="draft", local_id="draft-grouping-1"
    )
    assert first_draft_item is not None
    assert first_draft_item.target_id == str(created_draft_id)
    assert _find_receipt_item(
        first_receipt, bucket="created", entity_type="checkpoint", local_id="checkpoint-1"
    )

    assert not second_receipt.created
    assert _find_receipt_item(
        second_receipt, bucket="reused", entity_type="roster", local_id="roster-1"
    )
    second_draft_item = _find_receipt_item(
        second_receipt, bucket="reused", entity_type="draft", local_id="draft-grouping-1"
    )
    assert second_draft_item is not None
    assert second_draft_item.target_id == str(created_draft_id)
    assert _find_receipt_item(
        second_receipt, bucket="reused", entity_type="checkpoint", local_id="checkpoint-1"
    )

    rosters.save.assert_awaited_once()
    drafts.save_workspace.assert_awaited_once()
    grouping_export_jobs.create.assert_awaited_once()
    grouping_checkpoints.create.assert_awaited_once()
    assert id_generator.new_uuid.call_count == 4
    assert uow.entered is True
    assert uow.exited is True
