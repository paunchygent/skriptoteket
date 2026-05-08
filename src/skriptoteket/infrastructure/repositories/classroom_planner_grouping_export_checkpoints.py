"""PostgreSQL repository for classroom-planner grouping export checkpoints.

This module persists export-backed grouping history separately from mutable
draft workspaces, export jobs, and roster-owned smart rules. It gives smart
grouping a dedicated checkpoint seam with deterministic, label-insensitive
assignment hashes.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
    NormalizedGroupingSnapshot,
)
from skriptoteket.infrastructure.db.models.classroom_planner_grouping_export_checkpoint import (
    GroupingExportCheckpointModel,
)
from skriptoteket.protocols.classroom_planner import (
    GroupingExportCheckpointRepositoryProtocol,
)

SMART_GROUPING_HISTORY_WINDOW = 12


class PostgreSQLGroupingExportCheckpointRepository(GroupingExportCheckpointRepositoryProtocol):
    """Persist export-backed grouping checkpoints in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(self, checkpoint: GroupingExportCheckpoint) -> GroupingExportCheckpointModel:
        return GroupingExportCheckpointModel(
            id=checkpoint.id,
            roster_id=checkpoint.roster_id,
            template_id=checkpoint.template_id,
            source_draft_id=checkpoint.source_draft_id,
            source_kind=checkpoint.source_kind.value,
            source_export_job_id=checkpoint.source_export_job_id,
            source_share_artifact_id=checkpoint.source_share_artifact_id,
            assignment_hash=checkpoint.assignment_hash,
            grouping_snapshot=checkpoint.grouping_snapshot.model_dump(mode="json"),
            created_at=checkpoint.created_at,
        )

    def _to_checkpoint(self, model: GroupingExportCheckpointModel) -> GroupingExportCheckpoint:
        return GroupingExportCheckpoint(
            id=model.id,
            roster_id=model.roster_id,
            template_id=model.template_id,
            source_draft_id=model.source_draft_id,
            source_kind=model.source_kind,
            source_export_job_id=model.source_export_job_id,
            source_share_artifact_id=model.source_share_artifact_id,
            assignment_hash=model.assignment_hash,
            grouping_snapshot=NormalizedGroupingSnapshot.model_validate(model.grouping_snapshot),
            created_at=model.created_at,
        )

    async def list_recent_for_roster(
        self,
        *,
        roster_id: UUID,
    ) -> list[GroupingExportCheckpoint]:
        result = await self._session.execute(
            select(GroupingExportCheckpointModel)
            .where(GroupingExportCheckpointModel.roster_id == roster_id)
            .order_by(
                GroupingExportCheckpointModel.created_at.desc(),
                GroupingExportCheckpointModel.id.desc(),
            )
            .limit(SMART_GROUPING_HISTORY_WINDOW)
        )
        return [self._to_checkpoint(model) for model in result.scalars().all()]

    async def create(
        self,
        *,
        checkpoint: GroupingExportCheckpoint,
    ) -> GroupingExportCheckpoint:
        model = self._to_model(checkpoint)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_checkpoint(model)
