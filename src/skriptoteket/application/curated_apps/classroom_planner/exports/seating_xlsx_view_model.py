"""Workbook view models for classroom-planner seating XLSX exports.

Purpose:
    Project one hydrated seating workspace into a teacher-facing spatial grid
    so the XLSX export keeps the classroom's visual row/column meaning instead
    of flattening the plan into a coordinate list.

Relationships:
    - Built from `ClassroomPlannerWorkspace` in the application layer.
    - Consumed by the classroom-planner seating XLSX renderer in
      `infrastructure.curated_apps.apps.classroom_planner`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    Seat,
)
from skriptoteket.domain.errors import validation_error

_ROOM_GRID_UNIT = 96


class SeatingXlsxGridCell(BaseModel):
    """Describe one visible seat cell in the workbook seating grid."""

    model_config = ConfigDict(frozen=True)

    seat_label: str
    student_name: str | None = None


class SeatingXlsxGridRow(BaseModel):
    """Describe one rendered row in the workbook seating grid."""

    model_config = ConfigDict(frozen=True)

    cells: tuple[SeatingXlsxGridCell | None, ...]


class SeatingXlsxWorkbookViewModel(BaseModel):
    """Describe the full teacher-facing seating workbook."""

    model_config = ConfigDict(frozen=True)

    roster_name: str
    output_filename: str
    grid_rows: tuple[SeatingXlsxGridRow, ...]
    unplaced_student_names: tuple[str, ...]


def build_seating_xlsx_view_model(
    *,
    workspace: ClassroomPlannerWorkspace,
) -> SeatingXlsxWorkbookViewModel:
    """Project one seating workspace into workbook-ready teacher grid data."""

    template = workspace.template
    if template is None:
        raise validation_error("Välj klassrum innan du exporterar sittschemat.")

    students_by_id = {student.id: student for student in workspace.roster.students}
    seats_by_id = {seat.id: seat for seat in template.seats}
    assigned_students_by_seat_id: dict[str, str] = {}
    assigned_student_ids: set[str] = set()

    for assignment in workspace.seat_assignments:
        student = students_by_id.get(assignment.student_id)
        seat = seats_by_id.get(assignment.seat_id)
        if student is None or seat is None:
            raise validation_error(
                "Sittplaceringsexporten innehåller ogiltiga elev- eller platsreferenser."
            )
        if assignment.seat_id in assigned_students_by_seat_id:
            raise validation_error("Sittplaceringsexporten innehåller dubbla elevplaceringar.")
        assigned_students_by_seat_id[assignment.seat_id] = student.display_name
        assigned_student_ids.add(assignment.student_id)

    grid_rows = _build_grid_rows(
        seats=tuple(sorted(template.seats, key=_seat_sort_key)),
        assigned_students_by_seat_id=assigned_students_by_seat_id,
    )
    unplaced_student_names = tuple(
        sorted(
            (
                student.display_name
                for student in workspace.roster.students
                if student.id not in assigned_student_ids
            ),
            key=lambda name: name.casefold(),
        )
    )

    return SeatingXlsxWorkbookViewModel(
        roster_name=workspace.roster.name,
        output_filename=f"{_slugify(workspace.roster.name)}-sittplacering.xlsx",
        grid_rows=grid_rows,
        unplaced_student_names=unplaced_student_names,
    )


def _build_grid_rows(
    *,
    seats: tuple[Seat, ...],
    assigned_students_by_seat_id: dict[str, str],
) -> tuple[SeatingXlsxGridRow, ...]:
    """Build a sparse visual seat grid that preserves aisle gaps."""

    if not seats:
        return ()

    row_positions = sorted({_grid_coordinate_to_index(seat.y) for seat in seats})
    column_positions = sorted({_grid_coordinate_to_index(seat.x) for seat in seats})
    normalized_row_positions = _normalize_positions(row_positions)
    normalized_column_positions = _normalize_positions(column_positions)
    matrix: list[list[SeatingXlsxGridCell | None]] = [
        [None for _ in range(max(normalized_column_positions.values()) + 1)]
        for _ in range(max(normalized_row_positions.values()) + 1)
    ]

    for seat in seats:
        row_index = normalized_row_positions[_grid_coordinate_to_index(seat.y)]
        column_index = normalized_column_positions[_grid_coordinate_to_index(seat.x)]
        if matrix[row_index][column_index] is not None:
            raise validation_error(
                "Sittplaceringsexporten innehåller flera platser på samma koordinat."
            )
        matrix[row_index][column_index] = SeatingXlsxGridCell(
            seat_label=_format_seat_label(seat.id),
            student_name=assigned_students_by_seat_id.get(seat.id),
        )

    return tuple(SeatingXlsxGridRow(cells=tuple(row)) for row in matrix)


def _normalize_positions(indices: list[int]) -> dict[int, int]:
    """Shift raw teacher indices down to a zero-based grid while preserving gaps."""

    minimum_index = min(indices)
    return {index: index - minimum_index for index in indices}


def _seat_sort_key(seat: Seat) -> tuple[int, int, str]:
    """Sort seats by visible classroom position first."""

    return (_grid_coordinate_to_index(seat.y), _grid_coordinate_to_index(seat.x), seat.id)


def _grid_coordinate_to_index(value: int) -> int:
    """Convert room-grid pixel coordinates into one-based teacher indices."""

    if value < 0:
        raise validation_error("Sittplaceringsexporten innehåller negativa koordinater.")
    return (value // _ROOM_GRID_UNIT) + 1


def _format_seat_label(seat_id: str) -> str:
    """Mirror the planner's teacher-facing seat label style."""

    if seat_id.lower().startswith("seat-"):
        return f"plats-{seat_id[5:]}"
    return seat_id


def _slugify(value: str) -> str:
    """Build a conservative teacher-safe filename stem."""

    filtered = [character.lower() if character.isalnum() else "-" for character in value.strip()]
    slug = "".join(filtered).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "klassrumskarta"
