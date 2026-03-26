"""Grouping export presentation models for classroom-planner artifacts.

Purpose:
    Define the shared renderer-independent presentation contract for grouping
    exports so later XLSX and PDF artifacts can consume the same ordered,
    teacher-facing data without depending on the live planner DOM.

Relationships:
    - Built from `ClassroomPlannerWorkspace` in the application layer.
    - Serialized by the classroom-planner grouping export API.
    - Consumed later by grouping XLSX and PDF renderers.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    PlanDraftKind,
)
from skriptoteket.domain.errors import validation_error


class GroupingExportKind(StrEnum):
    """Enumerate the teacher-facing grouping export kinds."""

    XLSX = "xlsx"
    PDF = "pdf"


class GroupingExportPaperSize(StrEnum):
    """Enumerate the supported grouping PDF page contracts."""

    A4_PORTRAIT = "a4_portrait"


class GroupingPresentationMember(BaseModel):
    """Describe one ordered student inside a teacher-facing group export."""

    model_config = ConfigDict(frozen=True)

    member_order: int
    display_name: str


class GroupingPresentationGroup(BaseModel):
    """Describe one ordered teacher-facing group in the export contract."""

    model_config = ConfigDict(frozen=True)

    group_label: str
    group_order: int
    members: tuple[GroupingPresentationMember, ...]


class GroupingExportPresentation(BaseModel):
    """Describe the shared grouping presentation consumed by export renderers."""

    model_config = ConfigDict(frozen=True)

    draft_id: UUID
    class_name: str
    title: str
    filename_stem: str
    groups: tuple[GroupingPresentationGroup, ...]


class PreparedGroupingExportContract(BaseModel):
    """Describe the prepared public grouping export contract."""

    model_config = ConfigDict(frozen=True)

    grouping_draft_id: UUID
    roster_id: UUID
    export_kind: GroupingExportKind
    paper_size: GroupingExportPaperSize | None = None
    presentation: GroupingExportPresentation


def build_grouping_export_presentation(
    *,
    workspace: ClassroomPlannerWorkspace,
) -> GroupingExportPresentation:
    """Project one active grouping workspace into the shared export contract."""

    if workspace.draft.draft_kind is not PlanDraftKind.GROUPING:
        raise validation_error("Endast grupputkast kan exporteras från den här exportvägen.")

    assignment_by_student_id = {}
    for assignment in workspace.group_assignments:
        if assignment.student_id in assignment_by_student_id:
            raise validation_error("Grupperingsexporten innehåller dubbla grupptilldelningar.")
        assignment_by_student_id[assignment.student_id] = assignment.group_id
    members_by_group_id: dict[str, list[GroupingPresentationMember]] = {
        group.id: [] for group in workspace.groups
    }
    member_order_by_group_id: dict[str, int] = {group.id: 0 for group in workspace.groups}

    for student in workspace.roster.students:
        group_id = assignment_by_student_id.get(student.id)
        if group_id is None:
            continue
        if group_id not in members_by_group_id:
            raise validation_error("Grupperingsexporten innehåller ogiltiga gruppreferenser.")
        member_order_by_group_id[group_id] += 1
        members_by_group_id[group_id].append(
            GroupingPresentationMember(
                member_order=member_order_by_group_id[group_id],
                display_name=student.display_name,
            )
        )

    groups = tuple(
        GroupingPresentationGroup(
            group_label=group.name,
            group_order=group.sort_order,
            members=tuple(members_by_group_id[group.id]),
        )
        for group in sorted(
            workspace.groups, key=lambda item: (item.sort_order, item.name.casefold())
        )
    )

    return GroupingExportPresentation(
        draft_id=workspace.draft.id,
        class_name=workspace.roster.name,
        title="Gruppindelning",
        filename_stem=f"{_slugify(workspace.roster.name)}-gruppindelning",
        groups=groups,
    )


def _slugify(value: str) -> str:
    """Build a conservative teacher-safe filename stem."""

    filtered = [character.lower() if character.isalnum() else "-" for character in value.strip()]
    slug = "".join(filtered).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "klassrumskarta"
