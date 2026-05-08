"""PostgreSQL repository for classroom-planner seating export checkpoints.

This module persists export-backed seating history separately from mutable
draft workspaces, export jobs, and roster-owned smart rules. It gives later
smart-assignment slices a dedicated checkpoint seam with deterministic room and
assignment hashes.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedSeatingSnapshot,
    SeatingExportCheckpoint,
    SeatingRoomContextSnapshot,
)
from skriptoteket.infrastructure.db.models.classroom_planner_seating_export_checkpoint import (
    SeatingExportCheckpointModel,
)
from skriptoteket.protocols.classroom_planner import (
    SeatingExportCheckpointRepositoryProtocol,
)

SMART_SEATING_HISTORY_WINDOW = 12


class PostgreSQLSeatingExportCheckpointRepository(SeatingExportCheckpointRepositoryProtocol):
    """Persist export-backed seating checkpoints in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(self, checkpoint: SeatingExportCheckpoint) -> SeatingExportCheckpointModel:
        return SeatingExportCheckpointModel(
            id=checkpoint.id,
            roster_id=checkpoint.roster_id,
            template_id=checkpoint.template_id,
            source_draft_id=checkpoint.source_draft_id,
            source_kind=checkpoint.source_kind.value,
            source_export_job_id=checkpoint.source_export_job_id,
            source_share_artifact_id=checkpoint.source_share_artifact_id,
            room_context_hash=checkpoint.room_context_hash,
            assignment_hash=checkpoint.assignment_hash,
            room_context=checkpoint.room_context.model_dump(mode="json"),
            seating_snapshot=checkpoint.seating_snapshot.model_dump(mode="json"),
            created_at=checkpoint.created_at,
        )

    def _to_checkpoint(self, model: SeatingExportCheckpointModel) -> SeatingExportCheckpoint:
        return SeatingExportCheckpoint(
            id=model.id,
            roster_id=model.roster_id,
            template_id=model.template_id,
            source_draft_id=model.source_draft_id,
            source_kind=model.source_kind,
            source_export_job_id=model.source_export_job_id,
            source_share_artifact_id=model.source_share_artifact_id,
            room_context_hash=model.room_context_hash,
            assignment_hash=model.assignment_hash,
            room_context=SeatingRoomContextSnapshot.model_validate(model.room_context),
            seating_snapshot=NormalizedSeatingSnapshot.model_validate(model.seating_snapshot),
            created_at=model.created_at,
        )

    async def get_latest_for_roster_and_room_context(
        self,
        *,
        roster_id: UUID,
        room_context_hash: str,
    ) -> SeatingExportCheckpoint | None:
        result = await self._session.execute(
            select(SeatingExportCheckpointModel)
            .where(
                SeatingExportCheckpointModel.roster_id == roster_id,
                SeatingExportCheckpointModel.room_context_hash == room_context_hash,
            )
            .order_by(
                SeatingExportCheckpointModel.created_at.desc(),
                SeatingExportCheckpointModel.id.desc(),
            )
            .limit(1)
        )
        model = result.scalar_one_or_none()
        return self._to_checkpoint(model) if model else None

    async def list_recent_for_roster_and_room_context(
        self,
        *,
        roster_id: UUID,
        room_context_hash: str,
    ) -> list[SeatingExportCheckpoint]:
        result = await self._session.execute(
            select(SeatingExportCheckpointModel)
            .where(
                SeatingExportCheckpointModel.roster_id == roster_id,
                SeatingExportCheckpointModel.room_context_hash == room_context_hash,
            )
            .order_by(
                SeatingExportCheckpointModel.created_at.desc(),
                SeatingExportCheckpointModel.id.desc(),
            )
            .limit(SMART_SEATING_HISTORY_WINDOW)
        )
        return [self._to_checkpoint(model) for model in result.scalars().all()]

    async def create(
        self,
        *,
        checkpoint: SeatingExportCheckpoint,
    ) -> SeatingExportCheckpoint:
        model = self._to_model(checkpoint)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_checkpoint(model)
