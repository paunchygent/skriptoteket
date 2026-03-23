"""Repository contract tests for classroom planner draft-history review fixes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    SeatAssignment,
    StudentPlanningMeta,
)
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import PlanDraftModel
from skriptoteket.infrastructure.repositories.classroom_planner import (
    PostgreSQLPlanDraftRepository,
)


def _make_grouping_draft(
    *, draft_id: object, owner_user_id: object, roster_id: object, now: datetime
) -> PlanDraft:
    """Build a grouping draft with stable defaults for repository tests."""

    return PlanDraft(
        id=draft_id,
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        template_id=None,
        status=PlanDraftStatus.ACTIVE,
        revision=0,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_seating_draft(
    *,
    draft_id: object,
    owner_user_id: object,
    roster_id: object,
    now: datetime,
    template_id: object,
) -> PlanDraft:
    """Build a seating draft with stable defaults for repository tests."""

    return PlanDraft(
        id=draft_id,
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=0,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )


def _make_draft_model(
    *,
    draft: PlanDraft,
    now: datetime,
    history_stack: list[dict] | None = None,
    undo_index: int = 0,
) -> PlanDraftModel:
    """Build a mutable draft row for repository unit tests."""

    return PlanDraftModel(
        id=draft.id,
        owner_user_id=draft.owner_user_id,
        roster_id=draft.roster_id,
        draft_kind=draft.draft_kind.value,
        template_id=draft.template_id,
        status=draft.status.value,
        revision=draft.revision,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
        history_stack=history_stack,
        undo_index=undo_index,
        groups=[],
        group_assignments=[],
        seat_assignments=[],
        student_planning_meta=[],
    )


def _require_history(model: PlanDraftModel) -> list[dict]:
    """Return non-null history for assertions in repository contract tests."""

    assert model.history_stack is not None
    return model.history_stack


def _first_group_id(snapshot: dict) -> str:
    """Extract the first group id from a stored snapshot with runtime type checks."""

    raw_groups = snapshot["groups"]
    assert isinstance(raw_groups, list)
    first_group = raw_groups[0]
    assert isinstance(first_group, dict)
    group_id = first_group["id"]
    assert isinstance(group_id, str)
    return group_id


@pytest.mark.asyncio
async def test_first_step_undo_seeds_blank_grouping_state() -> None:
    """The first grouping edit should undo back to the initial blank state."""

    session = AsyncMock()
    repo = PostgreSQLPlanDraftRepository(session)

    draft_id = uuid4()
    owner_id = uuid4()
    roster_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = _make_grouping_draft(
        draft_id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        now=now,
    )
    model = _make_draft_model(draft=draft, now=now)
    session.get.return_value = model

    edited_workspace = DraftWorkspace(
        draft=draft.model_copy(update={"revision": 1}),
        groups=[DraftGroup(id="g1", name="G1", sort_order=0)],
        group_assignments=[],
        seat_assignments=[],
        student_planning_meta=[],
    )

    await repo.save_workspace(workspace=edited_workspace)

    history = _require_history(model)
    assert len(history) == 2
    assert model.undo_index == 1
    assert history[0]["groups"] == []
    assert history[1]["groups"] == [
        {"id": "g1", "name": "G1", "sort_order": 0, "name_is_custom": False}
    ]


@pytest.mark.asyncio
async def test_snapshot_coverage_includes_meta_and_template() -> None:
    """Grouping history snapshots should capture context and student planning metadata."""

    session = AsyncMock()
    repo = PostgreSQLPlanDraftRepository(session)

    draft_id = uuid4()
    owner_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = _make_grouping_draft(
        draft_id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        now=now,
    ).model_copy(update={"template_id": template_id})
    model = _make_draft_model(draft=draft.model_copy(update={"template_id": None}), now=now)
    session.get.return_value = model

    workspace = DraftWorkspace(
        draft=draft,
        groups=[],
        group_assignments=[],
        seat_assignments=[],
        student_planning_meta=[StudentPlanningMeta(student_id="s1", notes="test")],
    )

    await repo.save_workspace(workspace=workspace)

    history = _require_history(model)
    assert len(history) == 2
    snapshot = history[1]
    assert snapshot["template_id"] == str(template_id)
    assert snapshot["student_planning_meta"] == [
        {
            "student_id": "s1",
            "teacher_proximity": 0,
            "stability_preference": 0,
            "preferred_zone": None,
            "avoid_zone": None,
            "notes": "test",
        }
    ]


@pytest.mark.asyncio
async def test_redo_branch_truncation_clears_forward_history() -> None:
    """Saving after undo should discard stale forward history before appending."""

    session = AsyncMock()
    repo = PostgreSQLPlanDraftRepository(session)

    draft_id = uuid4()
    owner_id = uuid4()
    roster_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = _make_grouping_draft(
        draft_id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        now=now,
    )
    history = [
        {
            "template_id": None,
            "groups": [{"id": "g1", "name": "G1", "sort_order": 0, "name_is_custom": False}],
            "group_assignments": [],
            "student_planning_meta": [],
        },
        {
            "template_id": None,
            "groups": [{"id": "g2", "name": "G2", "sort_order": 0, "name_is_custom": False}],
            "group_assignments": [],
            "student_planning_meta": [],
        },
        {
            "template_id": None,
            "groups": [{"id": "g3", "name": "G3", "sort_order": 0, "name_is_custom": False}],
            "group_assignments": [],
            "student_planning_meta": [],
        },
    ]
    model = _make_draft_model(draft=draft, now=now, history_stack=history, undo_index=0)
    session.get.return_value = model

    workspace = DraftWorkspace(
        draft=draft.model_copy(update={"revision": 1}),
        groups=[DraftGroup(id="new", name="New", sort_order=0)],
        group_assignments=[],
        seat_assignments=[],
        student_planning_meta=[],
    )

    await repo.save_workspace(workspace=workspace)

    history = _require_history(model)
    assert len(history) == 2
    assert _first_group_id(history[0]) == "g1"
    assert _first_group_id(history[1]) == "new"
    assert model.undo_index == 1


@pytest.mark.asyncio
async def test_logically_identical_snapshots_do_not_append_history() -> None:
    """Equivalent grouping state with different list ordering should reuse the same history tip."""

    session = AsyncMock()
    repo = PostgreSQLPlanDraftRepository(session)

    draft_id = uuid4()
    owner_id = uuid4()
    roster_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = _make_grouping_draft(
        draft_id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        now=now,
    )
    model = _make_draft_model(draft=draft, now=now)
    session.get.return_value = model

    first_workspace = DraftWorkspace(
        draft=draft.model_copy(update={"revision": 1}),
        groups=[DraftGroup(id="group-a", name="Grupp A", sort_order=0)],
        group_assignments=[
            GroupAssignment(student_id="student-2", group_id="group-a"),
            GroupAssignment(student_id="student-1", group_id="group-a"),
        ],
        seat_assignments=[],
        student_planning_meta=[
            StudentPlanningMeta(student_id="student-2", notes="b"),
            StudentPlanningMeta(student_id="student-1", notes="a"),
        ],
    )

    await repo.save_workspace(workspace=first_workspace)

    second_workspace = DraftWorkspace(
        draft=first_workspace.draft.model_copy(update={"revision": 2}),
        groups=list(reversed(first_workspace.groups)),
        group_assignments=list(reversed(first_workspace.group_assignments)),
        seat_assignments=[],
        student_planning_meta=list(reversed(first_workspace.student_planning_meta)),
    )

    await repo.save_workspace(workspace=second_workspace)

    history = _require_history(model)
    assert len(history) == 2
    assert model.undo_index == 1


@pytest.mark.asyncio
async def test_seating_template_switch_resets_history_to_the_new_classroom_context() -> None:
    """Switching classrooms in seating should start a fresh in-draft history baseline."""

    session = AsyncMock()
    repo = PostgreSQLPlanDraftRepository(session)

    draft_id = uuid4()
    owner_id = uuid4()
    roster_id = uuid4()
    current_template_id = uuid4()
    previous_template_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = _make_seating_draft(
        draft_id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        now=now,
        template_id=current_template_id,
    )
    model = _make_draft_model(
        draft=draft.model_copy(update={"template_id": previous_template_id}),
        now=now,
    )
    session.get.return_value = model

    workspace = DraftWorkspace(
        draft=draft,
        groups=[],
        group_assignments=[],
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-2")],
        student_planning_meta=[StudentPlanningMeta(student_id="student-1", notes="front row")],
    )

    await repo.save_workspace(workspace=workspace)

    history = _require_history(model)
    assert len(history) == 1
    assert "template_id" not in history[0]
    assert history[0]["seat_assignments"] == [{"student_id": "student-1", "seat_id": "seat-2"}]
    assert history[0]["student_planning_meta"] == [
        {
            "student_id": "student-1",
            "teacher_proximity": 0,
            "stability_preference": 0,
            "preferred_zone": None,
            "avoid_zone": None,
            "notes": "front row",
        }
    ]
    assert model.undo_index == 0


@pytest.mark.asyncio
async def test_seating_undo_restores_assignments_without_restoring_template_id() -> None:
    """Undoing a seating change must restore seat state without undoing classroom selection."""

    session = AsyncMock()
    repo = PostgreSQLPlanDraftRepository(session)

    draft_id = uuid4()
    owner_id = uuid4()
    roster_id = uuid4()
    current_template_id = uuid4()
    now = datetime.now(timezone.utc)
    draft = _make_seating_draft(
        draft_id=draft_id,
        owner_user_id=owner_id,
        roster_id=roster_id,
        now=now,
        template_id=current_template_id,
    )
    history = [
        {
            "groups": [],
            "group_assignments": [],
            "seat_assignments": [],
            "student_planning_meta": [],
        },
        {
            "groups": [],
            "group_assignments": [],
            "seat_assignments": [{"student_id": "student-1", "seat_id": "seat-2"}],
            "student_planning_meta": [],
        },
    ]
    model = _make_draft_model(draft=draft, now=now, history_stack=history, undo_index=1)
    session.get.return_value = model

    restored_workspace = await repo.undo(draft_id=draft_id)

    assert restored_workspace is not None
    assert restored_workspace.draft.template_id == current_template_id
    assert restored_workspace.seat_assignments == []
    assert model.template_id == current_template_id
    assert model.undo_index == 0
