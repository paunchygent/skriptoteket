"""Openpyxl renderer for classroom-planner seating XLSX exports.

Purpose:
    Generate the teacher-facing seating workbook locally inside Skriptoteket so
    seating XLSX exports reuse the explicit export-job lane without depending
    on Sir Convert-a-Lot.

Relationships:
    - Implements `SeatingXlsxRendererProtocol`.
    - Consumes the application-layer seating XLSX workbook view model.
"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    seating_xlsx_view_model,
)
from skriptoteket.protocols.classroom_planner_exports import SeatingXlsxRendererProtocol

_HEADER_FILL = PatternFill(fill_type="solid", fgColor="1F2937")
_SECTION_FILL = PatternFill(fill_type="solid", fgColor="E5E7EB")
_HEADER_FONT = Font(color="FFFFFF", bold=True)
_TITLE_FONT = Font(size=16, bold=True)
_SECTION_FONT = Font(size=12, bold=True)
_BORDER = Border(bottom=Side(style="thin", color="1F2937"))


class SeatingXlsxRenderer(SeatingXlsxRendererProtocol):
    """Render the seating XLSX workbook bytes for one seating draft."""

    def render(self, *, view_model: seating_xlsx_view_model.SeatingXlsxWorkbookViewModel) -> bytes:
        workbook = Workbook()
        edit_sheet = workbook.active
        if edit_sheet is None:
            raise RuntimeError("Workbook did not create an active worksheet.")
        edit_sheet.title = "Redigera sittplatser"
        share_sheet = workbook.create_sheet(title="Dela och exportera")

        self._render_edit_sheet(edit_sheet, view_model=view_model)
        self._render_share_sheet(share_sheet, view_model=view_model)
        workbook.active = 0

        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    def _render_edit_sheet(
        self,
        worksheet,
        *,
        view_model: seating_xlsx_view_model.SeatingXlsxWorkbookViewModel,
    ) -> None:
        headers = ("Status", "Elevnamn", "Plats", "Rad", "Kolumn")
        worksheet.append(headers)
        for row in view_model.edit_rows:
            worksheet.append((row.status, row.student_name, row.seat_label, row.row, row.column))

        self._style_header_row(worksheet, row_number=1)
        worksheet.freeze_panes = "A2"
        worksheet.column_dimensions["A"].width = 16
        worksheet.column_dimensions["B"].width = 28
        worksheet.column_dimensions["C"].width = 14
        worksheet.column_dimensions["D"].width = 10
        worksheet.column_dimensions["E"].width = 10

        if view_model.edit_rows:
            table = Table(
                displayName="RedigeraSittplatser",
                ref=f"A1:E{len(view_model.edit_rows) + 1}",
            )
            # Excel tables already serialize their own autoFilter. Adding a
            # worksheet-level filter over the same range produces a workbook
            # Excel repairs by removing the table altogether.
            table.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False,
            )
            worksheet.add_table(table)

    def _render_share_sheet(
        self,
        worksheet,
        *,
        view_model: seating_xlsx_view_model.SeatingXlsxWorkbookViewModel,
    ) -> None:
        worksheet["A1"] = "Sittplacering"
        worksheet["A2"] = view_model.roster_name
        worksheet["A3"] = view_model.template_name
        worksheet["A1"].font = _TITLE_FONT
        worksheet["A2"].font = _SECTION_FONT
        worksheet["A3"].font = Font(italic=True)

        placed_header_row = 5
        worksheet[f"A{placed_header_row}"] = "Plats"
        worksheet[f"B{placed_header_row}"] = "Elevnamn"
        worksheet[f"C{placed_header_row}"] = "Rad"
        worksheet[f"D{placed_header_row}"] = "Kolumn"
        self._style_header_row(worksheet, row_number=placed_header_row)

        placed_end_row = placed_header_row
        for offset, row in enumerate(view_model.placed_rows, start=1):
            current_row = placed_header_row + offset
            placed_end_row = current_row
            worksheet[f"A{current_row}"] = row.seat_label
            worksheet[f"B{current_row}"] = row.student_name
            worksheet[f"C{current_row}"] = row.row
            worksheet[f"D{current_row}"] = row.column

        unplaced_section_row = placed_end_row + 2
        worksheet[f"A{unplaced_section_row}"] = "Ej placerade elever"
        worksheet[f"A{unplaced_section_row}"].font = _SECTION_FONT
        worksheet[f"A{unplaced_section_row}"].fill = _SECTION_FILL
        worksheet[f"A{unplaced_section_row}"].border = _BORDER
        worksheet[f"A{unplaced_section_row + 1}"] = "Elevnamn"
        self._style_header_row(worksheet, row_number=unplaced_section_row + 1)
        for offset, student_name in enumerate(view_model.unplaced_student_names, start=2):
            worksheet[f"A{unplaced_section_row + offset}"] = student_name

        worksheet.column_dimensions["A"].width = 18
        worksheet.column_dimensions["B"].width = 28
        worksheet.column_dimensions["C"].width = 10
        worksheet.column_dimensions["D"].width = 10
        worksheet.freeze_panes = "A4"
        worksheet.page_setup.paperSize = worksheet.PAPERSIZE_A4
        worksheet.page_setup.orientation = worksheet.ORIENTATION_LANDSCAPE
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.print_title_rows = "1:3"

    def _style_header_row(self, worksheet, *, row_number: int) -> None:
        for cell in worksheet[row_number]:
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.alignment = Alignment(horizontal="left", vertical="center")
            cell.border = _BORDER
