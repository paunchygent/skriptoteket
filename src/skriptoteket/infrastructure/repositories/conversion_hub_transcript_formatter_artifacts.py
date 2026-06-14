"""PostgreSQL repository for transcript formatter replay artifacts.

Domain purpose:
  Map persisted overlay-aware formatter artifact references between the
  Conversion Hub application contract and PostgreSQL.

Relationships:
  - Implements `ConversionHubTranscriptFormatterArtifactRepositoryProtocol`.
  - Uses `ConversionHubTranscriptFormatterArtifactModel` for storage.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.infrastructure.db.models.conversion_hub_transcript_formatter_artifact import (
    ConversionHubTranscriptFormatterArtifactModel,
)
from skriptoteket.protocols.conversion_hub import (
    ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
)


class PostgreSQLConversionHubTranscriptFormatterArtifactRepository(
    ConversionHubTranscriptFormatterArtifactRepositoryProtocol
):
    """Persist transcript formatter replay artifact references in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(
        self,
        record: ConversionHubTranscriptFormatterArtifactRecord,
    ) -> ConversionHubTranscriptFormatterArtifactModel:
        return ConversionHubTranscriptFormatterArtifactModel(
            id=record.id,
            owner_user_id=record.owner_user_id,
            saved_transcript_id=record.transcript_id,
            conversion_hub_job_id=record.conversion_hub_job_id,
            sir_convert_job_id=record.sir_convert_job_id,
            requested_artifact=record.requested_artifact.value,
            artifact_key=record.artifact_key.value,
            filename=record.filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            sha256=record.sha256,
            retrieval_path=record.retrieval_path,
            content=record.content,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _to_record(
        self,
        model: ConversionHubTranscriptFormatterArtifactModel,
    ) -> ConversionHubTranscriptFormatterArtifactRecord:
        return ConversionHubTranscriptFormatterArtifactRecord(
            id=model.id,
            owner_user_id=model.owner_user_id,
            transcript_id=model.saved_transcript_id,
            conversion_hub_job_id=model.conversion_hub_job_id,
            sir_convert_job_id=model.sir_convert_job_id,
            requested_artifact=model.requested_artifact,
            artifact_key=model.artifact_key,
            filename=model.filename,
            content_type=model.content_type,
            size_bytes=model.size_bytes,
            sha256=model.sha256,
            retrieval_path=model.retrieval_path,
            content=model.content,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def replace_for_replay(
        self,
        *,
        records: list[ConversionHubTranscriptFormatterArtifactRecord],
    ) -> list[ConversionHubTranscriptFormatterArtifactRecord]:
        if not records:
            return []
        owner_user_id = records[0].owner_user_id
        transcript_id = records[0].transcript_id
        await self._session.execute(
            delete(ConversionHubTranscriptFormatterArtifactModel).where(
                ConversionHubTranscriptFormatterArtifactModel.owner_user_id == owner_user_id,
                ConversionHubTranscriptFormatterArtifactModel.saved_transcript_id == transcript_id,
            )
        )
        self._session.add_all([self._to_model(record) for record in records])
        await self._session.flush()
        return records

    async def list_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> list[ConversionHubTranscriptFormatterArtifactRecord]:
        result = await self._session.execute(
            select(ConversionHubTranscriptFormatterArtifactModel)
            .where(
                ConversionHubTranscriptFormatterArtifactModel.owner_user_id == owner_user_id,
                ConversionHubTranscriptFormatterArtifactModel.saved_transcript_id == transcript_id,
            )
            .order_by(ConversionHubTranscriptFormatterArtifactModel.artifact_key)
        )
        return [self._to_record(model) for model in result.scalars().all()]

    async def get_by_owner_transcript_and_key(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
    ) -> ConversionHubTranscriptFormatterArtifactRecord | None:
        result = await self._session.execute(
            select(ConversionHubTranscriptFormatterArtifactModel).where(
                ConversionHubTranscriptFormatterArtifactModel.owner_user_id == owner_user_id,
                ConversionHubTranscriptFormatterArtifactModel.saved_transcript_id == transcript_id,
                ConversionHubTranscriptFormatterArtifactModel.artifact_key == artifact_key.value,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_record(model) if model is not None else None

    async def delete_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> None:
        await self._session.execute(
            delete(ConversionHubTranscriptFormatterArtifactModel).where(
                ConversionHubTranscriptFormatterArtifactModel.owner_user_id == owner_user_id,
                ConversionHubTranscriptFormatterArtifactModel.saved_transcript_id == transcript_id,
            )
        )
        await self._session.flush()
