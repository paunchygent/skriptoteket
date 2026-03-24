"""Behavior tests for classroom-planner seating export preparation.

This module focuses on the PR-0118 seam: preparing the typed seating export
contract and translating the active seating workspace into a deterministic
poster-scene model.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    PrepareSeatingExportHandler,
    SeatingExportKind,
    SeatingExportLayoutId,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneFixtureTone,
    PosterSceneFixtureVariant,
    PosterSceneLabelOrientation,
    PosterSceneWallSide,
    format_student_poster_label,
    translate_workspace_to_poster_scene,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftHistoryStatus,
    DraftWorkspace,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)

ROOM_GRID_UNIT = 96


@pytest.fixture
def drafts():
    return AsyncMock(spec=PlanDraftRepositoryProtocol)


@pytest.fixture
def rosters():
    return AsyncMock(spec=RosterRepositoryProtocol)


@pytest.fixture
def templates():
    return AsyncMock(spec=RoomTemplateRepositoryProtocol)


def _build_active_seating_draft(*, owner_user_id, roster_id, template_id) -> PlanDraft:
    now = datetime.now(timezone.utc)
    return PlanDraft(
        id=uuid4(),
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=2,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )


def _build_roster(*, owner_user_id, roster_id) -> Roster:
    now = datetime.now(timezone.utc)
    return Roster(
        id=roster_id,
        owner_user_id=owner_user_id,
        name="Klass 7A",
        students=[
            Student(id="student-1", display_name="Alice Andersson"),
            Student(id="student-2", display_name="Bo"),
        ],
        created_at=now,
        updated_at=now,
    )


def _build_template(*, owner_user_id, template_id) -> RoomTemplate:
    now = datetime.now(timezone.utc)
    return RoomTemplate(
        id=template_id,
        owner_user_id=owner_user_id,
        name="Sal A",
        grid_cols=14,
        grid_rows=9,
        seats=[
            Seat(id="seat-b", x=5 * ROOM_GRID_UNIT, y=2 * ROOM_GRID_UNIT),
            Seat(id="seat-a", x=1 * ROOM_GRID_UNIT, y=1 * ROOM_GRID_UNIT, zone="front"),
        ],
        fixtures=[
            RoomFixture(
                id="fixture-window",
                type=RoomFixtureType.WINDOW,
                x=12 * ROOM_GRID_UNIT,
                y=1 * ROOM_GRID_UNIT,
                width=2 * ROOM_GRID_UNIT,
                height=3 * ROOM_GRID_UNIT,
            ),
            RoomFixture(
                id="fixture-whiteboard",
                type=RoomFixtureType.WHITEBOARD,
                x=3 * ROOM_GRID_UNIT,
                y=0,
                width=4 * ROOM_GRID_UNIT,
                height=1 * ROOM_GRID_UNIT,
                label="Whiteboard",
            ),
            RoomFixture(
                id="fixture-whiteboard-2",
                type=RoomFixtureType.WHITEBOARD,
                x=7 * ROOM_GRID_UNIT,
                y=0,
                width=2 * ROOM_GRID_UNIT,
                height=1 * ROOM_GRID_UNIT,
                label="Whiteboard",
            ),
            RoomFixture(
                id="fixture-door",
                type=RoomFixtureType.DOOR,
                x=0,
                y=4 * ROOM_GRID_UNIT,
                width=1 * ROOM_GRID_UNIT,
                height=1 * ROOM_GRID_UNIT,
            ),
            RoomFixture(
                id="fixture-teacher-desk",
                type=RoomFixtureType.TEACHER_DESK,
                x=4 * ROOM_GRID_UNIT,
                y=1 * ROOM_GRID_UNIT,
                width=2 * ROOM_GRID_UNIT,
                height=1 * ROOM_GRID_UNIT,
                label="Kateder",
            ),
            RoomFixture(
                id="fixture-bench",
                type=RoomFixtureType.BENCH,
                x=9 * ROOM_GRID_UNIT,
                y=6 * ROOM_GRID_UNIT,
                width=1 * ROOM_GRID_UNIT,
                height=1 * ROOM_GRID_UNIT,
            ),
            RoomFixture(
                id="fixture-bench-2",
                type=RoomFixtureType.BENCH,
                x=10 * ROOM_GRID_UNIT,
                y=6 * ROOM_GRID_UNIT,
                width=1 * ROOM_GRID_UNIT,
                height=1 * ROOM_GRID_UNIT,
            ),
            RoomFixture(
                id="fixture-round-table",
                type=RoomFixtureType.ROUND_TABLE,
                x=7 * ROOM_GRID_UNIT,
                y=4 * ROOM_GRID_UNIT,
                width=2 * ROOM_GRID_UNIT,
                height=2 * ROOM_GRID_UNIT,
            ),
            RoomFixture(
                id="fixture-square-table",
                type=RoomFixtureType.SQUARE_TABLE,
                x=10 * ROOM_GRID_UNIT,
                y=4 * ROOM_GRID_UNIT,
                width=2 * ROOM_GRID_UNIT,
                height=2 * ROOM_GRID_UNIT,
            ),
        ],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_seating_export_returns_prepared_contract(drafts, rosters, templates):
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft = _build_active_seating_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        template_id=template_id,
    )
    drafts.get_workspace.return_value = DraftWorkspace(
        draft=draft,
        seat_assignments=[
            SeatAssignment(student_id="student-1", seat_id="seat-a"),
            SeatAssignment(student_id="student-2", seat_id="seat-b"),
        ],
        history_status=DraftHistoryStatus(can_undo=True, can_redo=False),
    )
    rosters.get_by_id.return_value = _build_roster(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
    )
    templates.get_by_id.return_value = _build_template(
        owner_user_id=owner_user_id,
        template_id=template_id,
    )
    handler = PrepareSeatingExportHandler(drafts=drafts, rosters=rosters, templates=templates)

    result = await handler.handle(
        draft_id=draft.id,
        owner_user_id=owner_user_id,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
    )

    assert result.seating_draft_id == draft.id
    assert result.export_kind == SeatingExportKind.PDF
    assert result.layout_id == SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER
    assert result.roster_name == "Klass 7A"
    assert result.template_name == "Sal A"
    assert [seat.seat_id for seat in result.poster_scene.seats] == ["seat-a", "seat-b"]
    assert result.poster_scene.seats[0].label == "Alice A."
    assert result.poster_scene.seats[1].label == "Bo B."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_seating_export_rejects_non_seating_draft(drafts, rosters, templates):
    owner_user_id = uuid4()
    draft = _build_active_seating_draft(
        owner_user_id=owner_user_id,
        roster_id=uuid4(),
        template_id=uuid4(),
    ).model_copy(update={"draft_kind": PlanDraftKind.GROUPING})
    drafts.get_workspace.return_value = DraftWorkspace(draft=draft)
    handler = PrepareSeatingExportHandler(drafts=drafts, rosters=rosters, templates=templates)

    with pytest.raises(DomainError) as error:
        await handler.handle(
            draft_id=draft.id,
            owner_user_id=owner_user_id,
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        )

    assert error.value.code == ErrorCode.VALIDATION_ERROR
    rosters.get_by_id.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_seating_export_rejects_inactive_draft(drafts, rosters, templates):
    owner_user_id = uuid4()
    draft = _build_active_seating_draft(
        owner_user_id=owner_user_id,
        roster_id=uuid4(),
        template_id=uuid4(),
    ).model_copy(update={"status": PlanDraftStatus.SUPERSEDED})
    drafts.get_workspace.return_value = DraftWorkspace(draft=draft)
    handler = PrepareSeatingExportHandler(drafts=drafts, rosters=rosters, templates=templates)

    with pytest.raises(DomainError) as error:
        await handler.handle(
            draft_id=draft.id,
            owner_user_id=owner_user_id,
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        )

    assert error.value.code == ErrorCode.CONFLICT
    rosters.get_by_id.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_seating_export_requires_classroom_context(drafts, rosters, templates):
    owner_user_id = uuid4()
    roster_id = uuid4()
    draft = _build_active_seating_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        template_id=None,
    )
    drafts.get_workspace.return_value = DraftWorkspace(draft=draft)
    rosters.get_by_id.return_value = _build_roster(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
    )
    handler = PrepareSeatingExportHandler(drafts=drafts, rosters=rosters, templates=templates)

    with pytest.raises(DomainError) as error:
        await handler.handle(
            draft_id=draft.id,
            owner_user_id=owner_user_id,
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        )

    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
def test_translate_workspace_to_poster_scene_preserves_export_markers_and_geometry():
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft = _build_active_seating_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        template_id=template_id,
    )
    workspace = ClassroomPlannerWorkspace(
        draft=draft,
        roster=_build_roster(owner_user_id=owner_user_id, roster_id=roster_id),
        template=_build_template(owner_user_id=owner_user_id, template_id=template_id),
        seat_assignments=[
            SeatAssignment(student_id="student-1", seat_id="seat-a"),
            SeatAssignment(student_id="student-2", seat_id="seat-b"),
        ],
    )

    scene = translate_workspace_to_poster_scene(workspace=workspace)

    assert scene.room.grid_cols == 14
    assert scene.room.grid_rows == 9
    fixture_by_id = {fixture.fixture_id: fixture for fixture in scene.fixtures}
    merged_whiteboard = next(
        fixture
        for fixture in scene.fixtures
        if fixture.source_fixture_ids == ("fixture-whiteboard", "fixture-whiteboard-2")
    )
    assert merged_whiteboard.kind == PosterSceneFixtureKind.WHITEBOARD
    assert merged_whiteboard.wall_side == PosterSceneWallSide.TOP
    assert merged_whiteboard.placement == PosterSceneFixturePlacement.WALL
    assert merged_whiteboard.label == "Whiteboard"
    assert merged_whiteboard.label_orientation == PosterSceneLabelOrientation.HORIZONTAL
    assert merged_whiteboard.tone == PosterSceneFixtureTone.OUTLINE
    assert merged_whiteboard.x == 3
    assert merged_whiteboard.width == 6
    assert fixture_by_id["fixture-door"].kind == PosterSceneFixtureKind.DOOR
    assert fixture_by_id["fixture-door"].wall_side == PosterSceneWallSide.LEFT
    assert fixture_by_id["fixture-door"].label == "Dörr"
    assert fixture_by_id["fixture-door"].label_orientation == PosterSceneLabelOrientation.VERTICAL
    assert fixture_by_id["fixture-window"].kind == PosterSceneFixtureKind.WINDOW
    assert fixture_by_id["fixture-window"].wall_side == PosterSceneWallSide.RIGHT
    assert fixture_by_id["fixture-window"].label == "Fönster"
    assert fixture_by_id["fixture-window"].label_orientation == PosterSceneLabelOrientation.VERTICAL
    assert fixture_by_id["fixture-teacher-desk"].kind == PosterSceneFixtureKind.TEACHER_DESK
    assert fixture_by_id["fixture-teacher-desk"].wall_side is None
    assert fixture_by_id["fixture-teacher-desk"].label == "Kateder"
    assert fixture_by_id["fixture-teacher-desk"].tone == PosterSceneFixtureTone.STRONG
    merged_bench = next(
        fixture
        for fixture in scene.fixtures
        if fixture.source_fixture_ids == ("fixture-bench", "fixture-bench-2")
    )
    assert merged_bench.kind == PosterSceneFixtureKind.BENCH
    assert merged_bench.placement == PosterSceneFixturePlacement.FLOOR
    assert merged_bench.label == "Bänk"
    assert merged_bench.width == 2
    assert fixture_by_id["fixture-round-table"].kind == PosterSceneFixtureKind.TABLE
    assert fixture_by_id["fixture-round-table"].variant == PosterSceneFixtureVariant.ROUND
    assert fixture_by_id["fixture-round-table"].label is None
    assert fixture_by_id["fixture-square-table"].variant == PosterSceneFixtureVariant.SQUARE


@pytest.mark.unit
def test_translate_workspace_to_poster_scene_rejects_unknown_seat_assignment_targets():
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft = _build_active_seating_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        template_id=template_id,
    )
    workspace = ClassroomPlannerWorkspace(
        draft=draft,
        roster=_build_roster(owner_user_id=owner_user_id, roster_id=roster_id),
        template=_build_template(owner_user_id=owner_user_id, template_id=template_id),
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="missing-seat")],
    )

    with pytest.raises(DomainError) as error:
        translate_workspace_to_poster_scene(workspace=workspace)

    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
def test_translate_workspace_to_poster_scene_does_not_merge_across_gaps_or_wall_changes():
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft = _build_active_seating_draft(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        template_id=template_id,
    )
    template = _build_template(owner_user_id=owner_user_id, template_id=template_id).model_copy(
        update={
            "fixtures": [
                RoomFixture(
                    id="bench-left",
                    type=RoomFixtureType.BENCH,
                    x=2 * ROOM_GRID_UNIT,
                    y=5 * ROOM_GRID_UNIT,
                    width=1 * ROOM_GRID_UNIT,
                    height=1 * ROOM_GRID_UNIT,
                ),
                RoomFixture(
                    id="bench-right",
                    type=RoomFixtureType.BENCH,
                    x=4 * ROOM_GRID_UNIT,
                    y=5 * ROOM_GRID_UNIT,
                    width=1 * ROOM_GRID_UNIT,
                    height=1 * ROOM_GRID_UNIT,
                ),
                RoomFixture(
                    id="whiteboard-top",
                    type=RoomFixtureType.WHITEBOARD,
                    x=3 * ROOM_GRID_UNIT,
                    y=0,
                    width=2 * ROOM_GRID_UNIT,
                    height=1 * ROOM_GRID_UNIT,
                ),
                RoomFixture(
                    id="whiteboard-right",
                    type=RoomFixtureType.WHITEBOARD,
                    x=13 * ROOM_GRID_UNIT,
                    y=2 * ROOM_GRID_UNIT,
                    width=1 * ROOM_GRID_UNIT,
                    height=2 * ROOM_GRID_UNIT,
                ),
            ]
        }
    )
    workspace = ClassroomPlannerWorkspace(
        draft=draft,
        roster=_build_roster(owner_user_id=owner_user_id, roster_id=roster_id),
        template=template,
        seat_assignments=[],
    )

    scene = translate_workspace_to_poster_scene(workspace=workspace)

    assert {fixture.source_fixture_ids for fixture in scene.fixtures} == {
        ("whiteboard-top",),
        ("whiteboard-right",),
        ("bench-left",),
        ("bench-right",),
    }
    whiteboard_right = next(
        fixture for fixture in scene.fixtures if fixture.source_fixture_ids == ("whiteboard-right",)
    )
    assert whiteboard_right.label_orientation == PosterSceneLabelOrientation.VERTICAL


@pytest.mark.unit
def test_format_student_poster_label_uses_first_name_and_last_initial_without_branching():
    assert (
        format_student_poster_label(Student(id="student-1", display_name="Alice Andersson"))
        == "Alice A."
    )
    assert format_student_poster_label(Student(id="student-2", display_name="Bo")) == "Bo B."
