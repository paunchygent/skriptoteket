"""Unit coverage for the plan-draft history snapshot round trip.

Snapshots are written by `create_workspace_snapshot`, stored as JSONB and read
back through `parse_workspace_snapshot` on undo/redo.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    SeatAssignment,
)
from skriptoteket.infrastructure.repositories.classroom_planner_plan_draft_mapping import (
    create_workspace_snapshot,
    parse_workspace_snapshot,
)


def _workspace(*, kind: PlanDraftKind) -> DraftWorkspace:
    now = datetime.now(timezone.utc)
    return DraftWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=uuid4(),
            roster_id=uuid4(),
            draft_kind=kind,
            template_id=uuid4(),
            smart_enabled=False,
            use_history=True,
            grouping_seating_distance_enabled=True,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        groups=[
            DraftGroup(id="g-2", name="Grupp 2", sort_order=1, name_is_custom=True),
            DraftGroup(id="g-1", name="Grupp 1", sort_order=0),
        ],
        group_assignments=[GroupAssignment(student_id="s-1", group_id="g-1")],
        seat_assignments=[SeatAssignment(student_id="s-1", seat_id="seat-1")],
    )


def _stored(snapshot: object) -> JsonValue:
    """Return the snapshot as the JSONB column hands it back."""
    stored: JsonValue = json.loads(json.dumps(snapshot))
    return stored


def test_snapshot_round_trips_through_json_for_grouping_draft() -> None:
    workspace = _workspace(kind=PlanDraftKind.GROUPING)
    snapshot = create_workspace_snapshot(workspace)

    parsed = parse_workspace_snapshot(_stored(snapshot))

    assert parsed == snapshot
    assert parsed["template_id"] == str(workspace.draft.template_id)
    assert [group["id"] for group in parsed["groups"]] == ["g-1", "g-2"]
    assert parsed["groups"][1]["name_is_custom"] is True
    assert parsed["smart_enabled"] is False
    assert parsed["use_history"] is True
    assert parsed["grouping_seating_distance_enabled"] is True


def test_snapshot_of_seating_draft_has_no_template_id() -> None:
    parsed = parse_workspace_snapshot(
        _stored(create_workspace_snapshot(_workspace(kind=PlanDraftKind.SEATING)))
    )

    assert "template_id" not in parsed


def test_parse_defaults_flags_seats_and_name_is_custom_when_keys_are_absent() -> None:
    parsed = parse_workspace_snapshot(
        {
            "groups": [{"id": "g-1", "name": "Grupp 1", "sort_order": 0}],
            "group_assignments": [],
        }
    )

    assert parsed == {
        "smart_enabled": False,
        "use_history": False,
        "grouping_seating_distance_enabled": False,
        "groups": [{"id": "g-1", "name": "Grupp 1", "sort_order": 0, "name_is_custom": False}],
        "group_assignments": [],
        "seat_assignments": [],
    }


def test_parse_coerces_template_id_and_flags_like_the_undo_path_always_did() -> None:
    parsed = parse_workspace_snapshot(
        {
            "smart_enabled": 1,
            "template_id": "",
            "groups": [],
            "group_assignments": [],
        }
    )

    assert parsed["smart_enabled"] is True
    assert parsed["template_id"] is None


def test_parse_raises_on_missing_required_key_and_on_wrong_field_type() -> None:
    with pytest.raises(KeyError):
        parse_workspace_snapshot({"group_assignments": []})
    with pytest.raises(TypeError):
        parse_workspace_snapshot(
            {
                "groups": [{"id": "g-1", "name": "Grupp 1", "sort_order": "0"}],
                "group_assignments": [],
            }
        )
    with pytest.raises(TypeError):
        parse_workspace_snapshot([])
