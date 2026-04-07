"""Route tests for public Klassrumskartan direct-download exports."""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import ANY, AsyncMock, Mock

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from skriptoteket.application.curated_apps.classroom_planner import (
    GroupingExportKind,
    RunPublicGroupingExportHandler,
    RunPublicSeatingExportHandler,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.public_export_contracts import (
    PublicExportDownload,
    PublicGroupingExportRequest,
    PublicSeatingExportRequest,
)
from skriptoteket.config import Settings
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
from skriptoteket.web.api.v1 import public_apps_classroom_planner_exports as api


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _make_app_definition() -> CuratedAppDefinition:
    app_id = "classroom.group-seating-studio"
    return CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Klassrumskartan",
        summary="Skapa sittplatsscheman och grupper automatiskt.",
        min_role=Role.USER,
        public_access_profile=CuratedAppPublicAccessProfile.PUBLIC_BROWSER_WORKSPACE_WITH_UPGRADE,
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
    )


def _registry() -> Mock:
    registry = Mock()
    registry.get_by_app_id.return_value = _make_app_definition()
    return registry


def _request(payload: dict[str, object]) -> Request:
    body = json.dumps(payload).encode("utf-8")

    async def receive() -> dict[str, object]:
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        },
        receive=receive,
    )
    request.state.correlation_id = None
    return request


def _snapshot_payload() -> dict[str, object]:
    return {
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_export_public_grouping_returns_attachment_response():
    handler = AsyncMock(spec=RunPublicGroupingExportHandler)
    handler.handle.return_value = PublicExportDownload(
        filename="gruppindelning.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        content=b"PK\x03\x04",
    )

    response = await _unwrap_dishka(api.export_public_grouping)(
        request=_request(
            {
                "snapshot": _snapshot_payload(),
                "expected_revision": 4,
                "export_kind": "xlsx",
                "paper_size": None,
            }
        ),
        registry=_registry(),
        settings=Settings(),
        clock=FixedClock(datetime(2026, 4, 7, 10, 0, 0)),
        throttle=InMemoryPublicHelperRequestThrottle(),
        handler=handler,
    )

    assert response.media_type == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["Content-Disposition"] == 'attachment; filename="gruppindelning.xlsx"'
    handler.handle.assert_awaited_once_with(
        snapshot=ANY,
        expected_revision=4,
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_export_public_seating_returns_attachment_response():
    handler = AsyncMock(spec=RunPublicSeatingExportHandler)
    handler.handle.return_value = PublicExportDownload(
        filename="klassrumskarta-a3.pdf",
        media_type="application/pdf",
        content=b"%PDF-1.7",
    )

    response = await _unwrap_dishka(api.export_public_seating)(
        request=_request(
            {
                "snapshot": _snapshot_payload(),
                "expected_revision": 2,
                "export_kind": "pdf",
                "layout_id": "pretty_brutalist_poster",
                "paper_size": "a3_landscape",
            }
        ),
        registry=_registry(),
        settings=Settings(),
        clock=FixedClock(datetime(2026, 4, 7, 10, 0, 0)),
        throttle=InMemoryPublicHelperRequestThrottle(),
        handler=handler,
    )

    assert response.media_type == "application/pdf"
    assert response.headers["Content-Disposition"] == 'attachment; filename="klassrumskarta-a3.pdf"'
    handler.handle.assert_awaited_once_with(
        snapshot=ANY,
        expected_revision=2,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
    )


@pytest.mark.unit
def test_public_grouping_export_request_rejects_non_a4_pdf_size():
    with pytest.raises(ValidationError):
        PublicGroupingExportRequest(
            snapshot=_snapshot_payload(),
            expected_revision=4,
            export_kind=GroupingExportKind.PDF,
            paper_size="letter_portrait",
        )


@pytest.mark.unit
def test_public_seating_export_request_rejects_xlsx_layout_inputs():
    with pytest.raises(ValidationError):
        PublicSeatingExportRequest(
            snapshot=_snapshot_payload(),
            expected_revision=2,
            export_kind=SeatingExportKind.XLSX,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        )
