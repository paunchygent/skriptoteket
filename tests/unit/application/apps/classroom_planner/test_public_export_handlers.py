"""Application tests for Klassrumskartan public direct-download export handlers.

Purpose:
    Lock down the defensive public export handler branches so invalid PDF input
    still fails as a domain validation error even if the web request layer is
    bypassed.

Relationships:
    - Exercises `RunPublicGroupingExportHandler` and
      `RunPublicSeatingExportHandler` directly.
    - Reuses the browser-owned guest snapshot payload contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    GroupingExportKind,
    RunPublicGroupingExportHandler,
    RunPublicSeatingExportHandler,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.grouping_exports import (
    PrepareGroupingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.seating_exports import (
    PrepareSeatingExportHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _snapshot() -> ClassroomPlannerGuestSnapshotPayload:
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
            "grouping_draft": {
                "local_id": "grouping-draft-1",
                "draft_kind": "grouping",
                "roster_local_id": "roster-1",
                "template_local_id": "template-1",
                "task_entry_classroom_selection_mode": "optional",
                "smart_enabled": False,
                "use_history": False,
                "grouping_seating_distance_enabled": False,
                "revision": 4,
                "last_opened_at": "2026-04-07T10:00:00Z",
                "groups": [
                    {"id": "group-a", "name": "Grupp 1", "sort_order": 0, "name_is_custom": False}
                ],
                "group_assignments": [{"student_id": "ada", "group_id": "group-a"}],
                "seat_assignments": [],
                "fingerprint": "sha256:grouping-draft",
            },
            "seating_draft": {
                "local_id": "seating-draft-1",
                "draft_kind": "seating",
                "roster_local_id": "roster-1",
                "template_local_id": "template-1",
                "task_entry_classroom_selection_mode": "required",
                "smart_enabled": False,
                "use_history": False,
                "grouping_seating_distance_enabled": False,
                "revision": 2,
                "last_opened_at": "2026-04-07T10:00:00Z",
                "groups": [],
                "group_assignments": [],
                "seat_assignments": [{"student_id": "alan", "seat_id": "seat-1"}],
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
                "fingerprint": "sha256:ui",
            },
        }
    )


@pytest.mark.asyncio
async def test_run_public_grouping_export_rejects_pdf_without_paper_size() -> None:
    handler = RunPublicGroupingExportHandler(
        prepare=PrepareGroupingExportHandler(
            drafts=Mock(),
            rosters=Mock(),
            templates=Mock(),
        ),
        pdf_renderer=Mock(),
        xlsx_renderer=Mock(),
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            snapshot=_snapshot(),
            expected_revision=4,
            export_kind=GroupingExportKind.PDF,
            paper_size=None,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_run_public_seating_export_rejects_pdf_without_layout() -> None:
    prepare = Mock(spec=PrepareSeatingExportHandler)
    handler = RunPublicSeatingExportHandler(
        prepare=prepare,
        pdf_renderer=Mock(),
        poster_renderer=Mock(),
        xlsx_renderer=Mock(),
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            snapshot=_snapshot(),
            expected_revision=2,
            export_kind=SeatingExportKind.PDF,
            layout_id=None,
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    prepare.build_prepared_contract.assert_not_called()


@pytest.mark.asyncio
async def test_run_public_seating_export_rejects_pdf_without_paper_size() -> None:
    prepare = Mock(spec=PrepareSeatingExportHandler)
    handler = RunPublicSeatingExportHandler(
        prepare=prepare,
        pdf_renderer=Mock(),
        poster_renderer=Mock(),
        xlsx_renderer=Mock(),
        clock=FixedClock(datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            snapshot=_snapshot(),
            expected_revision=2,
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            paper_size=None,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    prepare.build_prepared_contract.assert_not_called()
