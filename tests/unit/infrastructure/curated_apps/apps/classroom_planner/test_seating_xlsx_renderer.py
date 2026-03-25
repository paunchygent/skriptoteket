"""Unit tests for the classroom-planner seating XLSX renderer.

Purpose:
    Guard the workbook XML contract for the teacher-facing seating export so
    Excel-compatible table metadata stays valid when the workbook is opened.

Relationships:
    - Exercises `SeatingXlsxRenderer`.
    - Builds the workbook via the seating XLSX view-model projection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    seating_xlsx_view_model,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftHistoryStatus,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.seating_xlsx_renderer import (
    SeatingXlsxRenderer,
)

_SPREADSHEET_NS = {"ss": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _workspace() -> ClassroomPlannerWorkspace:
    now = datetime(2026, 3, 24, tzinfo=timezone.utc)
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft_id = uuid4()

    return ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=draft_id,
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
            template_id=template_id,
            status=PlanDraftStatus.ACTIVE,
            revision=1,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        roster=Roster(
            id=roster_id,
            owner_user_id=owner_user_id,
            name="Klass 7A",
            students=[
                Student(id="student-1", display_name="Ada Lovelace"),
                Student(id="student-2", display_name="Linus Torvalds"),
            ],
            created_at=now,
            updated_at=now,
        ),
        template=RoomTemplate(
            id=template_id,
            owner_user_id=owner_user_id,
            name="Sal A",
            seats=[Seat(id="seat-1", x=0, y=0)],
            fixtures=[],
            created_at=now,
            updated_at=now,
        ),
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-1")],
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


def _render_xml_parts() -> tuple[ElementTree.Element, ElementTree.Element]:
    view_model = seating_xlsx_view_model.build_seating_xlsx_view_model(workspace=_workspace())
    workbook_bytes = SeatingXlsxRenderer().render(view_model=view_model)

    with ZipFile(BytesIO(workbook_bytes)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml")
        table_xml = archive.read("xl/tables/table1.xml")

    return ElementTree.fromstring(sheet_xml), ElementTree.fromstring(table_xml)


@pytest.mark.unit
def test_edit_sheet_uses_table_filter_without_duplicate_worksheet_autofilter():
    sheet_root, table_root = _render_xml_parts()

    worksheet_filter = sheet_root.find("ss:autoFilter", _SPREADSHEET_NS)
    table_filter = table_root.find("ss:autoFilter", _SPREADSHEET_NS)

    assert worksheet_filter is None
    assert table_filter is not None
    assert table_filter.attrib["ref"] == "A1:E3"
    assert table_root.attrib["ref"] == "A1:E3"
