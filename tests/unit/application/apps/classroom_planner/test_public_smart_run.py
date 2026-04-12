"""Application tests for stateless public Smart helpers."""

from datetime import datetime, timezone

import pytest

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.public_smart_grouping import (
    NO_CLASSROOM_SIGNAL_MESSAGE,
    RunPublicSmartGroupingHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.public_smart_seating import (
    RunPublicSmartSeatingHandler,
)
from skriptoteket.domain.errors import DomainError


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _snapshot(*, grouping_use_history: bool = False) -> ClassroomPlannerGuestSnapshotPayload:
    return ClassroomPlannerGuestSnapshotPayload.model_validate(
        {
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
                        {"local_id": "bea", "display_name": "Bea"},
                        {"local_id": "cai", "display_name": "Cai"},
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
                        {"id": "seat-3", "x": 0, "y": 1, "zone": None},
                        {"id": "seat-4", "x": 1, "y": 1, "zone": None},
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
            "grouping_draft": {
                "local_id": "grouping-draft-1",
                "draft_kind": "grouping",
                "roster_local_id": "roster-1",
                "template_local_id": "template-1",
                "task_entry_classroom_selection_mode": "optional",
                "smart_enabled": True,
                "use_history": grouping_use_history,
                "grouping_seating_distance_enabled": True,
                "revision": 4,
                "last_opened_at": "2026-04-07T10:00:00Z",
                "groups": [
                    {"id": "group-a", "name": "Grupp 1", "sort_order": 0, "name_is_custom": False},
                    {"id": "group-b", "name": "Grupp 2", "sort_order": 1, "name_is_custom": False},
                ],
                "group_assignments": [
                    {"student_id": "ada", "group_id": "group-a"},
                    {"student_id": "alan", "group_id": "group-a"},
                    {"student_id": "bea", "group_id": "group-b"},
                    {"student_id": "cai", "group_id": "group-b"},
                ],
                "seat_assignments": [],
                "fingerprint": "sha256:grouping-draft",
            },
            "seating_draft": {
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
                    {"student_id": "bea", "seat_id": "seat-3"},
                    {"student_id": "cai", "seat_id": "seat-4"},
                ],
                "fingerprint": "sha256:seating-draft",
            },
            "checkpoint_descriptors": [],
            "ui_state": {
                "selected_roster_local_id": "roster-1",
                "selected_template_local_id": "template-1",
                "current_screen": "planner",
                "planner_initial_view": "groups",
                "dismissed_grouping_draft_local_id": None,
                "dismissed_seating_draft_local_id": None,
                "fingerprint": "sha256:ui-state",
            },
        }
    )


@pytest.mark.asyncio
async def test_run_public_smart_grouping_uses_guest_submitted_live_seating() -> None:
    handler = RunPublicSmartGroupingHandler(
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc))
    )

    result = await handler.handle(snapshot=_snapshot(), expected_revision=4)

    assert result.status == "applied"
    assert result.used_history is False
    assert result.used_live_seating is True
    assert result.workspace.draft.revision == 5
    assert len(result.workspace.group_assignments) == 4
    assert "stöd från klassens sittschema" in (result.message or "")


@pytest.mark.asyncio
async def test_run_public_smart_grouping_rejects_guest_use_history_flag() -> None:
    handler = RunPublicSmartGroupingHandler(
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc))
    )

    with pytest.raises(DomainError, match="Use history is account-only in guest Smart."):
        await handler.handle(snapshot=_snapshot(grouping_use_history=True), expected_revision=4)


@pytest.mark.asyncio
async def test_run_public_smart_grouping_rejects_revision_mismatch() -> None:
    handler = RunPublicSmartGroupingHandler(
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc))
    )

    with pytest.raises(DomainError, match="Draft revision mismatch"):
        await handler.handle(snapshot=_snapshot(), expected_revision=3)


@pytest.mark.asyncio
async def test_run_public_smart_seating_returns_browser_owned_workspace() -> None:
    handler = RunPublicSmartSeatingHandler(
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc))
    )

    result = await handler.handle(snapshot=_snapshot(), expected_revision=2)

    assert result.status == "applied"
    assert result.used_history is False
    assert result.workspace.draft.revision == 3
    assert len(result.workspace.seat_assignments) == 4
    assert result.message == "Smart placering klar."


@pytest.mark.asyncio
async def test_run_public_smart_seating_rejects_revision_mismatch() -> None:
    handler = RunPublicSmartSeatingHandler(
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc))
    )

    with pytest.raises(DomainError, match="Draft revision mismatch"):
        await handler.handle(snapshot=_snapshot(), expected_revision=1)


@pytest.mark.asyncio
async def test_run_public_smart_grouping_explains_missing_live_seating_context() -> None:
    base_snapshot = _snapshot()
    assert base_snapshot.seating_draft is not None
    snapshot = base_snapshot.model_copy(
        update={
            "seating_draft": base_snapshot.seating_draft.model_copy(
                update={"template_local_id": "template-2"}
            )
        }
    )
    handler = RunPublicSmartGroupingHandler(
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc))
    )

    result = await handler.handle(snapshot=snapshot, expected_revision=4)

    assert result.status == "applied"
    assert result.used_live_seating is False
    assert NO_CLASSROOM_SIGNAL_MESSAGE in (result.message or "")
