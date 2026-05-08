"""Checkpoint recorders for classroom-planner Smart history.

Purpose:
    Centralize creation and dedupe of export-backed Smart-history checkpoints
    so PDF/Excel exports and authenticated share links use the same durable
    history semantics.

Relationships:
    - Builds seating and grouping checkpoint domain objects from hydrated
      classroom-planner workspaces.
    - Consumed by export finalizers and authenticated share handlers inside
      their existing Unit of Work transactions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.checkpoint_provenance import (
    CheckpointSourceKind,
)
from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingExportCheckpoint,
    build_assignment_hash,
    build_normalized_seating_snapshot,
    build_room_context_hash,
    build_room_context_snapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
    build_grouping_assignment_hash,
    build_normalized_grouping_snapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
)
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
    SeatingExportCheckpointRepositoryProtocol,
)


class SeatingCheckpointRecorder:
    """Record deduped seating checkpoints for Smart-history consumers."""

    def __init__(
        self,
        *,
        checkpoints: SeatingExportCheckpointRepositoryProtocol,
    ) -> None:
        self._checkpoints = checkpoints

    async def record(
        self, *, checkpoint: SeatingExportCheckpoint
    ) -> SeatingExportCheckpoint | None:
        """Persist the checkpoint when it differs from the latest room-context match."""

        latest_checkpoint = await self._checkpoints.get_latest_for_roster_and_room_context(
            roster_id=checkpoint.roster_id,
            room_context_hash=checkpoint.room_context_hash,
        )
        if latest_checkpoint is not None and (
            latest_checkpoint.assignment_hash == checkpoint.assignment_hash
        ):
            return None
        return await self._checkpoints.create(checkpoint=checkpoint)


class GroupingCheckpointRecorder:
    """Record deduped grouping checkpoints for Smart-history consumers."""

    def __init__(
        self,
        *,
        checkpoints: GroupingExportCheckpointRepositoryProtocol,
    ) -> None:
        self._checkpoints = checkpoints

    async def record(
        self, *, checkpoint: GroupingExportCheckpoint
    ) -> GroupingExportCheckpoint | None:
        """Persist the checkpoint when it differs from the latest roster match."""

        latest_checkpoints = await self._checkpoints.list_recent_for_roster(
            roster_id=checkpoint.roster_id
        )
        latest_checkpoint = latest_checkpoints[0] if latest_checkpoints else None
        if latest_checkpoint is not None and (
            latest_checkpoint.assignment_hash == checkpoint.assignment_hash
        ):
            return None
        return await self._checkpoints.create(checkpoint=checkpoint)


def build_seating_checkpoint(
    *,
    workspace: ClassroomPlannerWorkspace,
    checkpoint_id: UUID,
    created_at: datetime,
    source_kind: CheckpointSourceKind,
    source_export_job_id: UUID | None = None,
    source_share_artifact_id: UUID | None = None,
) -> SeatingExportCheckpoint:
    """Build one seating checkpoint from an export or authenticated share source."""

    template = workspace.template
    if template is None:
        raise ValueError("Seating export checkpoints require a room template.")

    room_context = build_room_context_snapshot(workspace=workspace)
    seating_snapshot = build_normalized_seating_snapshot(workspace=workspace)
    return SeatingExportCheckpoint(
        id=checkpoint_id,
        roster_id=workspace.roster.id,
        template_id=template.id,
        source_draft_id=workspace.draft.id,
        source_kind=source_kind,
        source_export_job_id=source_export_job_id,
        source_share_artifact_id=source_share_artifact_id,
        room_context_hash=build_room_context_hash(room_context=room_context),
        assignment_hash=build_assignment_hash(seating_snapshot=seating_snapshot),
        room_context=room_context,
        seating_snapshot=seating_snapshot,
        created_at=created_at,
    )


def build_grouping_checkpoint(
    *,
    workspace: ClassroomPlannerWorkspace,
    checkpoint_id: UUID,
    created_at: datetime,
    source_kind: CheckpointSourceKind,
    source_export_job_id: UUID | None = None,
    source_share_artifact_id: UUID | None = None,
) -> GroupingExportCheckpoint:
    """Build one grouping checkpoint from an export or authenticated share source."""

    grouping_snapshot = build_normalized_grouping_snapshot(
        roster=workspace.roster,
        group_assignments=workspace.group_assignments,
    )
    return GroupingExportCheckpoint(
        id=checkpoint_id,
        roster_id=workspace.roster.id,
        template_id=workspace.template.id if workspace.template is not None else None,
        source_draft_id=workspace.draft.id,
        source_kind=source_kind,
        source_export_job_id=source_export_job_id,
        source_share_artifact_id=source_share_artifact_id,
        assignment_hash=build_grouping_assignment_hash(grouping_snapshot=grouping_snapshot),
        grouping_snapshot=grouping_snapshot,
        created_at=created_at,
    )
