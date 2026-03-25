"""Workbook view models for classroom-planner seating XLSX exports.

Purpose:
    Project one hydrated seating workspace into teacher-facing workbook data so
    the infrastructure renderer can generate a stable XLSX artifact without
    depending on planner web concerns or Sir Convert semantics.

Relationships:
    - Built from `ClassroomPlannerWorkspace` in the application layer.
    - Consumed by the classroom-planner seating XLSX renderer in
      `infrastructure.curated_apps.apps.classroom_planner`.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    Seat,
)
from skriptoteket.domain.errors import validation_error

_ROOM_GRID_UNIT = 96
_NO_TEMPLATE_LABEL = "Inget klassrum valt"


class SeatingXlsxEditRow(BaseModel):
    """Describe one teacher-editable seating row."""

    model_config = ConfigDict(frozen=True)

    status: str
    student_name: str
    seat_label: str
    row: int | None = None
    column: int | None = None


class SeatingXlsxPlacedRow(BaseModel):
    """Describe one placed student row for the share/export sheet."""

    model_config = ConfigDict(frozen=True)

    seat_label: str
    student_name: str
    row: int
    column: int


class SeatingXlsxWorkbookViewModel(BaseModel):
    """Describe the full teacher-facing seating workbook."""

    model_config = ConfigDict(frozen=True)

    roster_name: str
    template_name: str
    output_filename: str
    edit_rows: tuple[SeatingXlsxEditRow, ...]
    placed_rows: tuple[SeatingXlsxPlacedRow, ...]
    unplaced_student_names: tuple[str, ...]


def build_seating_xlsx_view_model(
    *,
    workspace: ClassroomPlannerWorkspace,
) -> SeatingXlsxWorkbookViewModel:
    """Project one seating workspace into workbook-ready teacher rows."""

    template = workspace.template
    if template is None:
        raise validation_error("Välj klassrum innan du exporterar sittschemat.")

    students_by_id = {student.id: student for student in workspace.roster.students}
    seats_by_id = {seat.id: seat for seat in template.seats}
    assigned_student_ids = {assignment.student_id for assignment in workspace.seat_assignments}

    placed_rows: list[SeatingXlsxPlacedRow] = []
    edit_rows: list[SeatingXlsxEditRow] = []
    for assignment in sorted(
        workspace.seat_assignments,
        key=lambda item: (
            _seat_sort_key(seats_by_id.get(item.seat_id)),
            item.student_id,
        ),
    ):
        student = students_by_id.get(assignment.student_id)
        seat = seats_by_id.get(assignment.seat_id)
        if student is None or seat is None:
            raise validation_error(
                "Sittplaceringsexporten innehåller ogiltiga elev- eller platsreferenser."
            )
        seat_row = _grid_coordinate_to_index(seat.y)
        seat_column = _grid_coordinate_to_index(seat.x)
        seat_label = _format_seat_label(seat.id)
        placed_rows.append(
            SeatingXlsxPlacedRow(
                seat_label=seat_label,
                student_name=student.display_name,
                row=seat_row,
                column=seat_column,
            )
        )
        edit_rows.append(
            SeatingXlsxEditRow(
                status="Placerad",
                student_name=student.display_name,
                seat_label=seat_label,
                row=seat_row,
                column=seat_column,
            )
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
    edit_rows.extend(
        SeatingXlsxEditRow(
            status="Ej placerad",
            student_name=student_name,
            seat_label="",
        )
        for student_name in unplaced_student_names
    )

    return SeatingXlsxWorkbookViewModel(
        roster_name=workspace.roster.name,
        template_name=template.name if template is not None else _NO_TEMPLATE_LABEL,
        output_filename=f"{_slugify(workspace.roster.name)}-sittplacering.xlsx",
        edit_rows=tuple(edit_rows),
        placed_rows=tuple(placed_rows),
        unplaced_student_names=unplaced_student_names,
    )


def _seat_sort_key(seat: Seat | None) -> tuple[int, int, str]:
    """Sort seat-backed rows by visible classroom position first."""

    if seat is None:
        return (10**9, 10**9, "")
    return (_grid_coordinate_to_index(seat.y), _grid_coordinate_to_index(seat.x), seat.id)


def _grid_coordinate_to_index(value: int) -> int:
    """Convert room-grid pixel coordinates into one-based teacher indices."""

    if value < 0:
        raise validation_error("Sittplaceringsexporten innehåller negativa koordinater.")
    return (value // _ROOM_GRID_UNIT) + 1


def _format_seat_label(seat_id: str) -> str:
    """Mirror the planner's teacher-facing seat label style."""

    return re.sub(r"^seat-", "plats-", seat_id, flags=re.IGNORECASE)


def _slugify(value: str) -> str:
    """Build a conservative teacher-safe filename stem."""

    filtered = [character.lower() if character.isalnum() else "-" for character in value.strip()]
    slug = "".join(filtered).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "klassrumskarta"
