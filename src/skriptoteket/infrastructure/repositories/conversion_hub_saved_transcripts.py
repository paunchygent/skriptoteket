"""PostgreSQL repositories for durable Conversion Hub transcripts.

Domain purpose:
  Map saved transcript JSON records and speaker display-name overlays between
  the Conversion Hub application contract and PostgreSQL so canonical
  transcript data survives upstream TTLs without rewriting speaker labels.

Relationships:
  - Implements Conversion Hub transcript repository protocols.
  - Uses transcript persistence models from the infrastructure DB model package.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
)
from skriptoteket.infrastructure.db.models.conversion_hub_saved_transcript import (
    ConversionHubSavedTranscriptModel,
)
from skriptoteket.infrastructure.db.models.conversion_hub_transcript_speaker_overlay import (
    ConversionHubTranscriptSpeakerOverlayModel,
)
from skriptoteket.protocols.conversion_hub import (
    ConversionHubSavedTranscriptRepositoryProtocol,
    ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
)


class PostgreSQLConversionHubSavedTranscriptRepository(
    ConversionHubSavedTranscriptRepositoryProtocol
):
    """Persist saved transcript JSON records in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(
        self,
        record: ConversionHubSavedTranscript,
    ) -> ConversionHubSavedTranscriptModel:
        return ConversionHubSavedTranscriptModel(
            id=record.id,
            owner_user_id=record.owner_user_id,
            conversion_hub_job_id=record.conversion_hub_job_id,
            sir_convert_job_id=record.sir_convert_job_id,
            artifact_key=record.artifact_key,
            source_filename=record.source_filename,
            transcript_schema_version=record.transcript_schema_version,
            language_code=record.language_code,
            diarization_mode=record.diarization_mode,
            speaker_count=record.speaker_count,
            speaker_min=record.speaker_min,
            speaker_max=record.speaker_max,
            generated_at=record.generated_at,
            correlation_id=record.correlation_id,
            transcript_json=record.transcript_json,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _to_record(
        self,
        model: ConversionHubSavedTranscriptModel,
    ) -> ConversionHubSavedTranscript:
        return ConversionHubSavedTranscript(
            id=model.id,
            owner_user_id=model.owner_user_id,
            conversion_hub_job_id=model.conversion_hub_job_id,
            sir_convert_job_id=model.sir_convert_job_id,
            artifact_key=model.artifact_key,
            source_filename=model.source_filename,
            transcript_schema_version=model.transcript_schema_version,
            language_code=model.language_code,
            diarization_mode=model.diarization_mode,
            speaker_count=model.speaker_count,
            speaker_min=model.speaker_min,
            speaker_max=model.speaker_max,
            generated_at=model.generated_at,
            correlation_id=model.correlation_id,
            transcript_json=model.transcript_json,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(
        self,
        *,
        record: ConversionHubSavedTranscript,
    ) -> ConversionHubSavedTranscript:
        model = self._to_model(record)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_record(model)

    async def get_by_owner_and_id(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> ConversionHubSavedTranscript | None:
        result = await self._session.execute(
            select(ConversionHubSavedTranscriptModel).where(
                ConversionHubSavedTranscriptModel.id == transcript_id,
                ConversionHubSavedTranscriptModel.owner_user_id == owner_user_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_record(model) if model is not None else None

    async def get_by_owner_and_upstream_job(
        self,
        *,
        owner_user_id: UUID,
        sir_convert_job_id: str,
    ) -> ConversionHubSavedTranscript | None:
        result = await self._session.execute(
            select(ConversionHubSavedTranscriptModel).where(
                ConversionHubSavedTranscriptModel.owner_user_id == owner_user_id,
                ConversionHubSavedTranscriptModel.sir_convert_job_id == sir_convert_job_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_record(model) if model is not None else None


class PostgreSQLConversionHubTranscriptSpeakerOverlayRepository(
    ConversionHubTranscriptSpeakerOverlayRepositoryProtocol
):
    """Persist transcript speaker overlays in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(
        self,
        overlay: ConversionHubTranscriptSpeakerOverlay,
    ) -> ConversionHubTranscriptSpeakerOverlayModel:
        return ConversionHubTranscriptSpeakerOverlayModel(
            id=overlay.id,
            owner_user_id=overlay.owner_user_id,
            saved_transcript_id=overlay.transcript_id,
            canonical_speaker_label=overlay.canonical_speaker_label,
            display_name=overlay.display_name,
            created_at=overlay.created_at,
            updated_at=overlay.updated_at,
        )

    def _to_record(
        self,
        model: ConversionHubTranscriptSpeakerOverlayModel,
    ) -> ConversionHubTranscriptSpeakerOverlay:
        return ConversionHubTranscriptSpeakerOverlay(
            id=model.id,
            owner_user_id=model.owner_user_id,
            transcript_id=model.saved_transcript_id,
            canonical_speaker_label=model.canonical_speaker_label,
            display_name=model.display_name,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def list_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> list[ConversionHubTranscriptSpeakerOverlay]:
        result = await self._session.execute(
            select(ConversionHubTranscriptSpeakerOverlayModel)
            .where(
                ConversionHubTranscriptSpeakerOverlayModel.owner_user_id == owner_user_id,
                ConversionHubTranscriptSpeakerOverlayModel.saved_transcript_id == transcript_id,
            )
            .order_by(ConversionHubTranscriptSpeakerOverlayModel.canonical_speaker_label)
        )
        return [self._to_record(model) for model in result.scalars().all()]

    async def replace_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
        overlays: list[ConversionHubTranscriptSpeakerOverlay],
    ) -> list[ConversionHubTranscriptSpeakerOverlay]:
        await self._session.execute(
            delete(ConversionHubTranscriptSpeakerOverlayModel).where(
                ConversionHubTranscriptSpeakerOverlayModel.owner_user_id == owner_user_id,
                ConversionHubTranscriptSpeakerOverlayModel.saved_transcript_id == transcript_id,
            )
        )
        self._session.add_all([self._to_model(overlay) for overlay in overlays])
        await self._session.flush()
        return await self.list_for_transcript(
            owner_user_id=owner_user_id,
            transcript_id=transcript_id,
        )
