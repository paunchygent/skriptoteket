"""DTOs and serializers for class-workspace planner summaries.

This module keeps the class-first workspace read-model contract separate from
the larger mutable planner route module. It serializes compact class workspace
data without coupling the frontend to full draft workspace payloads.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    ClassWorkspaceRosterSummary,
    ClassWorkspaceSummary,
    PlanDraftKind,
    PlanDraftStatus,
    PlanDraftSummary,
    TaskEntryOption,
)


class TaskEntryOptionDto(BaseModel):
    """Serialize one task-entry rule for the class workspace."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    draft_kind: PlanDraftKind
    classroom_selection_mode: ClassroomSelectionMode


class PlanDraftSummaryDto(BaseModel):
    """Serialize a compact draft summary for class-workspace surfaces."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    draft_kind: PlanDraftKind
    template_id: UUID | None = None
    template_name: str | None = None
    status: PlanDraftStatus
    revision: int
    last_opened_at: datetime
    updated_at: datetime


class ClassWorkspaceRosterSummaryDto(BaseModel):
    """Serialize compact class identity details for the workspace."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    name: str
    student_count: int


class ClassWorkspaceSummaryDto(BaseModel):
    """Serialize the class-first workspace summary."""

    model_config = ConfigDict(frozen=True)

    roster: ClassWorkspaceRosterSummaryDto
    task_entry_options: list[TaskEntryOptionDto]
    active_grouping_draft: PlanDraftSummaryDto | None = None
    active_seating_draft: PlanDraftSummaryDto | None = None
    grouping_history: list[PlanDraftSummaryDto]
    seating_history: list[PlanDraftSummaryDto]


def _serialize_task_entry_option(option: TaskEntryOption) -> TaskEntryOptionDto:
    """Map one task-entry domain model to the public API response."""

    return TaskEntryOptionDto.model_validate(option)


def _serialize_draft_summary(summary: PlanDraftSummary) -> PlanDraftSummaryDto:
    """Map one compact draft summary to the public API response."""

    return PlanDraftSummaryDto.model_validate(summary)


def _serialize_roster_summary(
    roster_summary: ClassWorkspaceRosterSummary,
) -> ClassWorkspaceRosterSummaryDto:
    """Map one compact roster summary to the public API response."""

    return ClassWorkspaceRosterSummaryDto.model_validate(roster_summary)


def serialize_class_workspace_summary(
    summary: ClassWorkspaceSummary,
) -> ClassWorkspaceSummaryDto:
    """Map the class-workspace read model to the public API response."""

    return ClassWorkspaceSummaryDto(
        roster=_serialize_roster_summary(summary.roster),
        task_entry_options=[
            _serialize_task_entry_option(option) for option in summary.task_entry_options
        ],
        active_grouping_draft=_serialize_draft_summary(summary.active_grouping_draft)
        if summary.active_grouping_draft
        else None,
        active_seating_draft=_serialize_draft_summary(summary.active_seating_draft)
        if summary.active_seating_draft
        else None,
        grouping_history=[_serialize_draft_summary(item) for item in summary.grouping_history],
        seating_history=[_serialize_draft_summary(item) for item in summary.seating_history],
    )
