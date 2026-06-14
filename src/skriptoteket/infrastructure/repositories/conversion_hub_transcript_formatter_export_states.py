"""PostgreSQL repository for transcript formatter export state.

Domain purpose:
  Store the product-owned formatter export request shape separately from
  verified artifact rows so pending, running, and failed states retain teacher
  intent without manufacturing artifacts.

Relationships:
  - Implements `ConversionHubTranscriptFormatterExportStateRepositoryProtocol`.
  - Uses `ConversionHubTranscriptFormatterExportStateModel` for persistence.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.conversion_hub_transcript_exports import (
    ConversionHubTranscriptFormatterExportStateRecord,
)
from skriptoteket.infrastructure.db.models.conversion_hub_transcript_formatter_export_state import (
    ConversionHubTranscriptFormatterExportStateModel,
)
from skriptoteket.protocols.conversion_hub import (
    ConversionHubTranscriptFormatterExportStateRepositoryProtocol,
)


class PostgreSQLTranscriptFormatterExportStateRepository(
    ConversionHubTranscriptFormatterExportStateRepositoryProtocol
):
    """Persist formatter export state records in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(
        self,
        record: ConversionHubTranscriptFormatterExportStateRecord,
    ) -> ConversionHubTranscriptFormatterExportStateModel:
        return ConversionHubTranscriptFormatterExportStateModel(
            id=record.id,
            owner_user_id=record.owner_user_id,
            saved_transcript_id=record.transcript_id,
            conversion_hub_job_id=record.conversion_hub_job_id,
            requested_artifacts=[artifact.value for artifact in record.requested_artifacts],
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _to_record(
        self,
        model: ConversionHubTranscriptFormatterExportStateModel,
    ) -> ConversionHubTranscriptFormatterExportStateRecord:
        return ConversionHubTranscriptFormatterExportStateRecord(
            id=model.id,
            owner_user_id=model.owner_user_id,
            transcript_id=model.saved_transcript_id,
            conversion_hub_job_id=model.conversion_hub_job_id,
            requested_artifacts=model.requested_artifacts,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def upsert(
        self,
        *,
        record: ConversionHubTranscriptFormatterExportStateRecord,
    ) -> ConversionHubTranscriptFormatterExportStateRecord:
        model = await self._find_by_job_id(
            owner_user_id=record.owner_user_id,
            conversion_hub_job_id=record.conversion_hub_job_id,
        )
        if model is None:
            model = self._to_model(record)
            self._session.add(model)
        else:
            model.saved_transcript_id = record.transcript_id
            model.requested_artifacts = [artifact.value for artifact in record.requested_artifacts]
            model.updated_at = record.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_record(model)

    async def get_by_job_id(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ConversionHubTranscriptFormatterExportStateRecord | None:
        model = await self._find_by_job_id(
            owner_user_id=owner_user_id,
            conversion_hub_job_id=conversion_hub_job_id,
        )
        return self._to_record(model) if model is not None else None

    async def _find_by_job_id(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ConversionHubTranscriptFormatterExportStateModel | None:
        result = await self._session.execute(
            select(ConversionHubTranscriptFormatterExportStateModel).where(
                ConversionHubTranscriptFormatterExportStateModel.owner_user_id == owner_user_id,
                ConversionHubTranscriptFormatterExportStateModel.conversion_hub_job_id
                == conversion_hub_job_id,
            )
        )
        return result.scalar_one_or_none()
