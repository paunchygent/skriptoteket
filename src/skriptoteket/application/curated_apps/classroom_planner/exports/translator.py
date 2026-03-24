"""Poster-scene translation for Klassrumskartan seating exports.

Purpose:
    Translate the mutable seating draft workspace plus roster and room-template
    geometry into a deterministic, standalone poster-scene model that later
    export-specific HTML/CSS rendering can consume.

Relationships:
    - Called by the seating export handler after owner-scoped draft loading.
    - Uses classroom-planner domain models as input but emits only application
      export models.
    - Mirrors the frontend room semantics for wall-bound fixtures while
      remaining renderer-independent and grid-based.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Seat,
    Student,
)
from skriptoteket.domain.errors import validation_error

from .models import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixtureVariant,
    PosterSceneRoom,
    PosterSceneSeat,
    PosterSceneWallSide,
    SeatingPosterScene,
)

ROOM_GRID_UNIT = 96


def format_student_poster_label(student: Student) -> str:
    """Format the canonical poster label as first name plus last initial."""

    tokens = [token for token in student.display_name.strip().split() if token]
    if not tokens:
        raise validation_error("Student display names must contain at least one visible token.")

    first_name = tokens[0]
    last_initial = _extract_initial(tokens[-1])
    return f"{first_name} {last_initial}."


def translate_workspace_to_poster_scene(
    *,
    workspace: ClassroomPlannerWorkspace,
) -> SeatingPosterScene:
    """Translate one hydrated seating workspace into a standalone poster scene."""

    template = workspace.template
    if template is None:
        raise validation_error("Välj klassrum innan du exporterar sittschemat.")

    students_by_id = {student.id: student for student in workspace.roster.students}
    seat_ids = {seat.id for seat in template.seats}
    _validate_export_assignments(
        workspace=workspace,
        seat_ids=seat_ids,
        student_ids=set(students_by_id),
    )
    assignments_by_seat_id = {
        assignment.seat_id: assignment for assignment in workspace.seat_assignments
    }

    seats = [
        _translate_seat(
            seat=seat,
            student=students_by_id.get(assignments_by_seat_id[seat.id].student_id)
            if seat.id in assignments_by_seat_id
            else None,
            student_id=assignments_by_seat_id[seat.id].student_id
            if seat.id in assignments_by_seat_id
            else None,
        )
        for seat in sorted(template.seats, key=lambda seat: (seat.y, seat.x, seat.id))
    ]
    fixtures = [
        _translate_fixture(fixture=fixture, template=template)
        for fixture in sorted(
            template.fixtures, key=lambda fixture: (fixture.y, fixture.x, fixture.type, fixture.id)
        )
    ]

    return SeatingPosterScene(
        room=PosterSceneRoom(
            grid_cols=template.grid_cols,
            grid_rows=template.grid_rows,
        ),
        seats=seats,
        fixtures=fixtures,
    )


def _translate_seat(
    *,
    seat: Seat,
    student: Student | None,
    student_id: str | None,
) -> PosterSceneSeat:
    """Translate one room seat plus its optional assignment into poster data."""

    if student_id is not None and student is None:
        raise validation_error(
            "Seat assignments must reference roster students before seating export is prepared."
        )

    return PosterSceneSeat(
        seat_id=seat.id,
        x=_normalize_grid_unit(seat.x),
        y=_normalize_grid_unit(seat.y),
        zone=seat.zone,
        student_id=student_id,
        label=format_student_poster_label(student) if student is not None else None,
    )


def _translate_fixture(
    *,
    fixture: RoomFixture,
    template: RoomTemplate,
) -> PosterSceneFixture:
    """Translate one room fixture into a poster marker."""

    kind, variant = _map_fixture_kind(fixture.type)
    return PosterSceneFixture(
        fixture_id=fixture.id,
        kind=kind,
        x=_normalize_grid_unit(fixture.x),
        y=_normalize_grid_unit(fixture.y),
        width=_normalize_fixture_span(fixture.width),
        height=_normalize_fixture_span(fixture.height),
        wall_side=_resolve_wall_side(fixture=fixture, template=template),
        label=fixture.label,
        variant=variant,
    )


def _map_fixture_kind(
    fixture_type: RoomFixtureType,
) -> tuple[PosterSceneFixtureKind, PosterSceneFixtureVariant | None]:
    """Normalize room-template fixture types into export fixture semantics."""

    if fixture_type == RoomFixtureType.WHITEBOARD:
        return PosterSceneFixtureKind.WHITEBOARD, None
    if fixture_type == RoomFixtureType.TEACHER_DESK:
        return PosterSceneFixtureKind.TEACHER_DESK, None
    if fixture_type == RoomFixtureType.DOOR:
        return PosterSceneFixtureKind.DOOR, None
    if fixture_type == RoomFixtureType.WINDOW:
        return PosterSceneFixtureKind.WINDOW, None
    if fixture_type == RoomFixtureType.BENCH:
        return PosterSceneFixtureKind.BENCH, None
    if fixture_type == RoomFixtureType.ROUND_TABLE:
        return PosterSceneFixtureKind.TABLE, PosterSceneFixtureVariant.ROUND
    if fixture_type == RoomFixtureType.SQUARE_TABLE:
        return PosterSceneFixtureKind.TABLE, PosterSceneFixtureVariant.SQUARE
    raise validation_error(
        "Room fixtures contain an unsupported export marker.",
        details={"fixture_type": fixture_type.value},
    )


def _resolve_wall_side(
    *,
    fixture: RoomFixture,
    template: RoomTemplate,
) -> PosterSceneWallSide | None:
    """Resolve the logical wall side for wall-bound fixtures."""

    if fixture.type not in {
        RoomFixtureType.WHITEBOARD,
        RoomFixtureType.WINDOW,
        RoomFixtureType.DOOR,
    }:
        return None

    fixture_x = _normalize_grid_unit(fixture.x)
    fixture_y = _normalize_grid_unit(fixture.y)
    fixture_width = _normalize_fixture_span(fixture.width)
    fixture_height = _normalize_fixture_span(fixture.height)
    prefers_vertical_wall = fixture.height >= fixture.width
    grid_width = template.grid_cols
    grid_height = template.grid_rows

    if prefers_vertical_wall:
        if fixture_x == 0:
            return PosterSceneWallSide.LEFT
        if fixture_x + fixture_width == grid_width:
            return PosterSceneWallSide.RIGHT

    if fixture_y == 0:
        return PosterSceneWallSide.TOP
    if fixture_y + fixture_height == grid_height:
        return PosterSceneWallSide.BOTTOM

    if not prefers_vertical_wall:
        if fixture_x == 0:
            return PosterSceneWallSide.LEFT
        if fixture_x + fixture_width == grid_width:
            return PosterSceneWallSide.RIGHT

    raise validation_error(
        "Wall-bound room markers must stay attached to the room boundary for export.",
        details={"fixture_id": fixture.id, "fixture_type": fixture.type.value},
    )


def _extract_initial(token: str) -> str:
    """Return the first visible alphanumeric character for initial formatting."""

    for character in token:
        if character.isalnum():
            return character.upper()
    raise validation_error("Student display names must contain alphanumeric characters.")


def _normalize_grid_unit(value: int) -> int:
    """Convert stored room geometry from planner units into logical grid units."""

    return round(value / ROOM_GRID_UNIT)


def _normalize_fixture_span(value: int) -> int:
    """Convert stored fixture dimensions into at least one logical grid unit."""

    return max(1, _normalize_grid_unit(value))


def _validate_export_assignments(
    *,
    workspace: ClassroomPlannerWorkspace,
    seat_ids: set[str],
    student_ids: set[str],
) -> None:
    """Reject export preparation when seating references leave the room scene."""

    assignment_seat_ids = [assignment.seat_id for assignment in workspace.seat_assignments]
    if len(assignment_seat_ids) != len(set(assignment_seat_ids)):
        raise validation_error("Seat assignments must remain unique before export is prepared.")

    for assignment in workspace.seat_assignments:
        if assignment.seat_id not in seat_ids:
            raise validation_error("Seat assignments must reference room seats before export.")
        if assignment.student_id not in student_ids:
            raise validation_error("Seat assignments must reference roster students before export.")
