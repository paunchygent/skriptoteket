"""Workbook view models for classroom-planner grouping XLSX exports.

Purpose:
    Project the shared grouping export presentation plus the current set of
    ungrouped students into a teacher-facing workbook structure with one flat
    edit sheet and one formula-linked presentation sheet.

Relationships:
    - Built from `GroupingExportPresentation` in the application layer.
    - Consumed by the classroom-planner grouping XLSX renderer in
      `infrastructure.curated_apps.apps.classroom_planner`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .grouping_presentation import GroupingExportPresentation


class GroupingXlsxEditRow(BaseModel):
    """Describe one teacher-visible edit row in the grouping workbook."""

    model_config = ConfigDict(frozen=True)

    member_order: int
    student_name: str
    group_label: str | None = None


class GroupingXlsxRegistryRow(BaseModel):
    """Describe one teacher-visible group registry row in the workbook."""

    model_config = ConfigDict(frozen=True)

    group_label: str
    group_order: int


class GroupingXlsxWorkbookViewModel(BaseModel):
    """Describe the full teacher-facing grouping workbook."""

    model_config = ConfigDict(frozen=True)

    title: str
    class_name: str
    generated_label: str
    output_filename: str
    edit_rows: tuple[GroupingXlsxEditRow, ...]
    registry_rows: tuple[GroupingXlsxRegistryRow, ...]
    sorted_row_capacity: int
    presentation_row_capacity: int


def build_grouping_xlsx_view_model(
    *,
    presentation: GroupingExportPresentation,
    generated_at: datetime,
    unassigned_student_names: tuple[str, ...] = (),
) -> GroupingXlsxWorkbookViewModel:
    """Project grouping export data into workbook-ready edit and print rows."""

    registry_rows = tuple(
        GroupingXlsxRegistryRow(
            group_label=group.group_label,
            group_order=group.group_order + 1,
        )
        for group in presentation.groups
    )
    assigned_rows = tuple(
        GroupingXlsxEditRow(
            member_order=member.member_order,
            student_name=member.display_name,
            group_label=group.group_label,
        )
        for group in presentation.groups
        for member in group.members
    )
    unassigned_rows = tuple(
        GroupingXlsxEditRow(
            group_label=None,
            group_order=None,
            member_order=index,
            student_name=student_name,
        )
        for index, student_name in enumerate(unassigned_student_names, start=1)
    )
    edit_rows = assigned_rows + unassigned_rows
    row_capacity = max(len(edit_rows), 1)
    group_count = max(len(registry_rows), 1)
    presentation_row_capacity = len(assigned_rows) + (3 * group_count) - 1 if registry_rows else 1

    return GroupingXlsxWorkbookViewModel(
        title=presentation.title,
        class_name=presentation.class_name,
        generated_label=f"Skapad {generated_at.strftime('%Y-%m-%d %H:%M')}",
        output_filename=f"{presentation.filename_stem}.xlsx",
        edit_rows=edit_rows,
        registry_rows=registry_rows,
        sorted_row_capacity=row_capacity,
        presentation_row_capacity=presentation_row_capacity,
    )
