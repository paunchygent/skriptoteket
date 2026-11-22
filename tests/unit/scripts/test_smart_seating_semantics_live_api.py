"""Unit tests for the live smart-seating semantics API layer, fed with real API response shapes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from uuid import uuid4

import requests
from pydantic import JsonValue
from requests import PreparedRequest, Response
from requests.adapters import BaseAdapter

from scripts._smart_seating_semantics_api import (
    create_seating_draft,
    get_g20_template,
    patch_draft,
    run_smart_seating,
)
from scripts._smart_seating_semantics_support import (
    SA24D_STUDENT_NAMES,
    build_topology,
    near_teacher_pool_seat_ids,
    rotated_assignments,
    student_id,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    PlanDraftKind,
)
from skriptoteket.web.api.v1.apps_classroom_planner import (
    DraftHistoryStatusDto,
    DraftWorkspaceResponse,
    RoomFixtureDto,
    RoomTemplateDto,
    RosterDto,
    SeatAssignmentDto,
    SeatDto,
    StudentDto,
)
from skriptoteket.web.api.v1.apps_classroom_planner_draft_contracts import PlanDraftDto

API_BASE_URL = "http://api.test"
SEAT_COUNT = 31


def _template_dto() -> RoomTemplateDto:
    return RoomTemplateDto(
        id=uuid4(),
        name="G20",
        grid_cols=12,
        grid_rows=8,
        seats=[
            SeatDto(id=f"seat-{index}", x=index % 8, y=2 + index // 8, zone="front")
            for index in range(SEAT_COUNT)
        ],
        fixtures=[
            RoomFixtureDto(
                id="board",
                type="whiteboard",
                x=0,
                y=0,
                width=6,
                height=1,
                label="Tavla",
            )
        ],
    )


def _draft_dto(*, revision: int) -> PlanDraftDto:
    return PlanDraftDto(
        id=uuid4(),
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        task_entry_classroom_selection_mode=ClassroomSelectionMode.OPTIONAL,
        status="active",
        revision=revision,
        last_opened_at=datetime.now(timezone.utc),
    )


def _workspace_dto(*, revision: int, seat_ids: list[str]) -> DraftWorkspaceResponse:
    return DraftWorkspaceResponse(
        draft=_draft_dto(revision=revision),
        roster=RosterDto(
            id=uuid4(),
            name="SA24D",
            students=[
                StudentDto(id=student_id(name), display_name=name) for name in SA24D_STUDENT_NAMES
            ],
        ),
        template=_template_dto(),
        groups=[],
        group_assignments=[],
        seat_assignments=[
            SeatAssignmentDto(student_id=student_id(name), seat_id=seat_id)
            for name, seat_id in zip(SA24D_STUDENT_NAMES, seat_ids, strict=True)
        ],
        history_status=DraftHistoryStatusDto(can_undo=False, can_redo=False),
    )


class _ScriptedAdapter(BaseAdapter):
    """Answer the next requests with queued JSON bodies, in order, and record what was sent."""

    def __init__(self, bodies: list[JsonValue]) -> None:
        super().__init__()
        self._bodies = bodies
        self.sent: list[tuple[str | None, str | None, JsonValue]] = []

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: None | float | tuple[float, float] | tuple[float, None] = None,
        verify: bool | str = True,
        cert: None | bytes | str | tuple[bytes | str, bytes | str] = None,
        proxies: Mapping[str, str] | None = None,
    ) -> Response:
        sent_body: JsonValue = None
        if isinstance(request.body, bytes):
            sent_body = json.loads(request.body)
        self.sent.append((request.method, request.url, sent_body))
        response = Response()
        response.status_code = 200
        response._content = json.dumps(self._bodies.pop(0)).encode("utf-8")
        return response


def _scripted_session(bodies: list[JsonValue]) -> tuple[requests.Session, _ScriptedAdapter]:
    adapter = _ScriptedAdapter(bodies)
    session = requests.Session()
    session.mount("http://", adapter)
    return session, adapter


def _json(model: PlanDraftDto | RoomTemplateDto | DraftWorkspaceResponse) -> JsonValue:
    body: JsonValue = json.loads(model.model_dump_json())
    return body


def test_template_response_reaches_build_topology_with_geometry_and_fixtures() -> None:
    template_dto = _template_dto()
    session, _adapter = _scripted_session(
        [
            [{"id": str(uuid4()), "name": "Other"}, {"id": str(template_dto.id), "name": "G20"}],
            _json(template_dto),
        ]
    )

    template = get_g20_template(session, api_base_url=API_BASE_URL)

    assert template["id"] == str(template_dto.id)
    assert (template["name"], template["grid_cols"], template["grid_rows"]) == ("G20", 12, 8)
    assert len(template["seats"]) == SEAT_COUNT
    assert [fixture["type"] for fixture in template["fixtures"]] == ["whiteboard"]
    topology = build_topology(template)
    assert set(topology.block_id_by_seat) == {seat["id"] for seat in template["seats"]}
    assert near_teacher_pool_seat_ids(topology)
    assignments = rotated_assignments(template, 3)
    assert len(assignments) == len(SA24D_STUDENT_NAMES)
    assert assignments[0] == {"student_id": "kerstin-aitman", "seat_id": "seat-3"}


def test_created_draft_keeps_the_revision_the_first_history_patch_sends() -> None:
    draft_dto = _draft_dto(revision=4)
    seat_ids = [f"seat-{index}" for index in range(SEAT_COUNT)]
    session, adapter = _scripted_session(
        [_json(draft_dto), _json(_workspace_dto(revision=5, seat_ids=seat_ids))]
    )

    draft = create_seating_draft(
        session,
        api_base_url=API_BASE_URL,
        csrf_token="token",
        roster_id=str(draft_dto.roster_id),
        template_id=str(draft_dto.template_id),
    )
    assert draft["id"] == str(draft_dto.id)
    assert draft["revision"] == 4

    new_revision = patch_draft(
        session,
        api_base_url=API_BASE_URL,
        csrf_token="token",
        draft_id=draft["id"],
        expected_revision=draft["revision"],
        smart_enabled=True,
    )

    assert new_revision == 5
    method, _url, payload = adapter.sent[-1]
    assert method == "PATCH"
    assert payload == {"expected_revision": 4, "smart_enabled": True}


def test_smart_run_result_keeps_workspace_revision_and_seat_assignments() -> None:
    seat_ids = [f"seat-{index}" for index in range(SEAT_COUNT)]
    workspace = _workspace_dto(revision=9, seat_ids=seat_ids)
    session, _adapter = _scripted_session(
        [
            {
                "status": "applied",
                "workspace": json.loads(workspace.model_dump_json()),
                "used_history": True,
                "message": "Smart placering klar med stöd av tidigare exporter.",
                "rule_diagnostics": [],
            }
        ]
    )

    result = run_smart_seating(
        session,
        api_base_url=API_BASE_URL,
        csrf_token="token",
        draft_id=str(uuid4()),
        expected_revision=8,
    )

    assert result["status"] == "applied"
    assert result["used_history"] is True
    assert result["workspace"]["draft"]["revision"] == 9
    assert result["workspace"]["seat_assignments"][0] == {
        "student_id": "kerstin-aitman",
        "seat_id": "seat-0",
    }
    assert len(result["workspace"]["seat_assignments"]) == len(SA24D_STUDENT_NAMES)
