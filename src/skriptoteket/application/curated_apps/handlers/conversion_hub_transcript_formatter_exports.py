"""Product-owned Conversion Hub transcript formatter export handlers.

Domain purpose:
  Own saved-transcript formatter export intent and state inside Skriptoteket
  while consuming Sir Convert's task-363 formatter producer from the backend.

Relationships:
  - Uses saved transcript, speaker overlay, job, and artifact repository
    protocols.
  - Calls `ConversionHubTranscriptFormatterProducerProtocol` for producer IO.
  - Returns product-safe export state to the transcript save API routes.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_exports import (
    ConversionHubTranscriptFormatterExportRequest,
    ConversionHubTranscriptFormatterExportResponse,
    ConversionHubTranscriptFormatterExportStateRecord,
    ConversionHubTranscriptFormatterExportStatus,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_formatter_contracts import (
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterArtifactRef,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_export_support as export_support,
)
from skriptoteket.domain.errors import DomainError, not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import (
    ConversionHubJobRepositoryProtocol,
    ConversionHubSavedTranscriptRepositoryProtocol,
    ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
    ConversionHubTranscriptFormatterExportArtifactRepositoryProtocol,
    ConversionHubTranscriptFormatterExportJobRepositoryProtocol,
    ConversionHubTranscriptFormatterExportStateRepositoryProtocol,
    ConversionHubTranscriptFormatterProducerProtocol,
    ConversionHubTranscriptFormatterProducerResult,
    ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class RequestConversionHubTranscriptFormatterExportHandler:
    """Create or refresh product-owned formatter export state."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        speaker_overlays: ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        export_states: ConversionHubTranscriptFormatterExportStateRepositoryProtocol,
        producer: ConversionHubTranscriptFormatterProducerProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._transcripts = transcripts
        self._speaker_overlays = speaker_overlays
        self._artifacts = artifacts
        self._export_states = export_states
        self._producer = producer
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        transcript_id: UUID,
        request: ConversionHubTranscriptFormatterExportRequest,
        correlation_id: str | None,
    ) -> ConversionHubTranscriptFormatterExportResponse:
        transcript, overlays = await self._load_export_inputs(
            actor=actor,
            transcript_id=transcript_id,
        )
        if not overlays:
            raise validation_error("Save speaker names before requesting transcript export.")
        export_support.validate_overlay_inventory(transcript=transcript, overlays=overlays)
        job_spec = export_support.build_export_job_spec(
            requested_artifacts=request.requested_artifacts,
            overlays=overlays,
        )
        producer_request = export_support.build_producer_request(
            transcript=transcript,
            job_spec=job_spec,
            requested_artifacts=request.requested_artifacts,
            correlation_id=correlation_id,
        )
        try:
            producer_result = await self._producer.create_transcript_formatter_export(
                request=producer_request
            )
        except DomainError as exc:
            return await self._record_failed_export(
                actor=actor,
                transcript=transcript,
                upstream_job_id=None,
                correlation_id=correlation_id,
                requested_artifacts=request.requested_artifacts,
                error_message=export_support.safe_error_message(exc),
            )
        return await self._record_producer_result(
            actor=actor,
            transcript=transcript,
            request=request,
            producer_result=producer_result,
            correlation_id=correlation_id,
        )

    async def _load_export_inputs(
        self,
        *,
        actor: User,
        transcript_id: UUID,
    ) -> tuple[ConversionHubSavedTranscript, list[ConversionHubTranscriptSpeakerOverlay]]:
        async with self._uow:
            transcript = await _load_transcript(
                transcripts=self._transcripts,
                actor=actor,
                transcript_id=transcript_id,
            )
            overlays = await self._speaker_overlays.list_for_transcript(
                owner_user_id=actor.id,
                transcript_id=transcript.id,
            )
        return transcript, overlays

    async def _record_producer_result(
        self,
        *,
        actor: User,
        transcript: ConversionHubSavedTranscript,
        request: ConversionHubTranscriptFormatterExportRequest,
        producer_result: ConversionHubTranscriptFormatterProducerResult,
        correlation_id: str | None,
    ) -> ConversionHubTranscriptFormatterExportResponse:
        if producer_result.status.strip().lower() == "succeeded":
            try:
                artifact_refs, artifact_content = export_support.verify_successful_export(
                    producer_result=producer_result,
                    requested_artifacts=request.requested_artifacts,
                )
            except DomainError as exc:
                return await self._record_failed_export(
                    actor=actor,
                    transcript=transcript,
                    upstream_job_id=producer_result.sir_convert_job_id,
                    correlation_id=correlation_id,
                    requested_artifacts=request.requested_artifacts,
                    error_message=export_support.safe_error_message(exc),
                )
            return await self._record_successful_export(
                actor=actor,
                transcript=transcript,
                producer_result=producer_result,
                artifact_refs=artifact_refs,
                artifact_content=artifact_content,
                correlation_id=correlation_id,
                requested_artifacts=request.requested_artifacts,
            )
        job_status = export_support.job_status_from_producer(producer_result.status)
        if job_status is ConversionHubJobStatus.SUCCEEDED:
            job_status = ConversionHubJobStatus.FAILED
        return await self._record_observed_export_state(
            actor=actor,
            transcript=transcript,
            upstream_job_id=producer_result.sir_convert_job_id,
            status=job_status,
            correlation_id=correlation_id,
            requested_artifacts=request.requested_artifacts,
            error_message=(
                producer_result.error_message
                if job_status is ConversionHubJobStatus.FAILED
                else None
            ),
        )

    async def _record_successful_export(
        self,
        *,
        actor: User,
        transcript: ConversionHubSavedTranscript,
        producer_result: ConversionHubTranscriptFormatterProducerResult,
        artifact_refs: list[ConversionHubTranscriptFormatterArtifactRef],
        artifact_content: dict[ConversionHubTranscriptFormatterArtifactKey, bytes],
        correlation_id: str | None,
        requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
    ) -> ConversionHubTranscriptFormatterExportResponse:
        if producer_result.sir_convert_job_id is None:
            raise validation_error("Sir Convert formatter response is missing job id.")
        async with self._uow:
            job = await self._create_or_update_job(
                actor=actor,
                transcript=transcript,
                upstream_job_id=producer_result.sir_convert_job_id,
                status=ConversionHubJobStatus.SUCCEEDED,
                correlation_id=correlation_id,
                error_message=None,
            )
            await self._upsert_export_state(
                actor=actor,
                transcript=transcript,
                job=job,
                requested_artifacts=requested_artifacts,
            )
            records = await self._artifacts.replace_for_export(
                records=_artifact_records(
                    actor=actor,
                    transcript=transcript,
                    job=job,
                    sir_convert_job_id=producer_result.sir_convert_job_id,
                    artifact_refs=artifact_refs,
                    artifact_content=artifact_content,
                    now=self._clock.now(),
                    id_generator=self._id_generator,
                )
            )
        return export_support.response_from_job_and_records(
            transcript_id=transcript.id,
            job=job,
            records=records,
            requested_artifacts=requested_artifacts,
        )

    async def _record_failed_export(
        self,
        *,
        actor: User,
        transcript: ConversionHubSavedTranscript,
        upstream_job_id: str | None,
        correlation_id: str | None,
        requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
        error_message: str | None,
    ) -> ConversionHubTranscriptFormatterExportResponse:
        return await self._record_observed_export_state(
            actor=actor,
            transcript=transcript,
            upstream_job_id=upstream_job_id,
            status=ConversionHubJobStatus.FAILED,
            correlation_id=correlation_id,
            requested_artifacts=requested_artifacts,
            error_message=error_message,
        )

    async def _record_observed_export_state(
        self,
        *,
        actor: User,
        transcript: ConversionHubSavedTranscript,
        upstream_job_id: str | None,
        status: ConversionHubJobStatus,
        correlation_id: str | None,
        requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
        error_message: str | None,
    ) -> ConversionHubTranscriptFormatterExportResponse:
        async with self._uow:
            job = await self._create_or_update_job(
                actor=actor,
                transcript=transcript,
                upstream_job_id=upstream_job_id,
                status=status,
                correlation_id=correlation_id,
                error_message=error_message if status is ConversionHubJobStatus.FAILED else None,
            )
            await self._upsert_export_state(
                actor=actor,
                transcript=transcript,
                job=job,
                requested_artifacts=requested_artifacts,
            )
            await self._artifacts.delete_for_transcript(
                owner_user_id=actor.id,
                transcript_id=transcript.id,
            )
        return export_support.response_from_job_and_records(
            transcript_id=transcript.id,
            job=job,
            records=[],
            requested_artifacts=requested_artifacts,
        )

    async def _upsert_export_state(
        self,
        *,
        actor: User,
        transcript: ConversionHubSavedTranscript,
        job: ConversionHubJob,
        requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
    ) -> ConversionHubTranscriptFormatterExportStateRecord:
        now = self._clock.now()
        existing = await self._export_states.get_by_job_id(
            owner_user_id=actor.id,
            conversion_hub_job_id=job.id,
        )
        created_at = existing.created_at if existing is not None else now
        record_id = existing.id if existing is not None else self._id_generator.new_uuid()
        return await self._export_states.upsert(
            record=ConversionHubTranscriptFormatterExportStateRecord(
                id=record_id,
                owner_user_id=actor.id,
                transcript_id=transcript.id,
                conversion_hub_job_id=job.id,
                requested_artifacts=requested_artifacts,
                created_at=created_at,
                updated_at=now,
            )
        )

    async def _create_or_update_job(
        self,
        *,
        actor: User,
        transcript: ConversionHubSavedTranscript,
        upstream_job_id: str | None,
        status: ConversionHubJobStatus,
        correlation_id: str | None,
        error_message: str | None,
    ) -> ConversionHubJob:
        existing = None
        if upstream_job_id is not None:
            existing = await self._jobs.get_by_upstream_job_id(upstream_job_id=upstream_job_id)
        if existing is not None:
            export_support.validate_existing_export_job(
                job=existing,
                actor=actor,
                transcript_id=transcript.id,
            )
            return await self._jobs.update(
                job=existing.model_copy(
                    update={
                        "status": status,
                        "correlation_id": correlation_id,
                        "error_message": error_message,
                        "updated_at": self._clock.now(),
                    }
                )
            )
        now = self._clock.now()
        return await self._jobs.create(
            job=ConversionHubJob(
                id=self._id_generator.new_uuid(),
                owner_user_id=actor.id,
                input_filename=export_support.local_export_input_filename(
                    transcript_id=transcript.id
                ),
                source_format=ConversionHubSourceFormatV2.TRANSCRIPT_JSON,
                output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
                pdf_layout=None,
                upstream_job_id=upstream_job_id,
                status=status,
                correlation_id=correlation_id,
                error_message=error_message,
                created_at=now,
                updated_at=now,
            )
        )


class GetConversionHubTranscriptFormatterExportHandler:
    """Read the latest product-owned formatter export state for a transcript."""

    def __init__(
        self,
        *,
        jobs: ConversionHubTranscriptFormatterExportJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterExportArtifactRepositoryProtocol,
        export_states: ConversionHubTranscriptFormatterExportStateRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._jobs = jobs
        self._transcripts = transcripts
        self._artifacts = artifacts
        self._export_states = export_states
        self._uow = uow

    async def handle(
        self,
        *,
        actor: User,
        transcript_id: UUID,
    ) -> ConversionHubTranscriptFormatterExportResponse:
        async with self._uow:
            transcript = await _load_transcript(
                transcripts=self._transcripts,
                actor=actor,
                transcript_id=transcript_id,
            )
            job = await self._jobs.get_latest_transcript_formatter_export(
                owner_user_id=actor.id,
                input_filename=export_support.local_export_input_filename(
                    transcript_id=transcript.id
                ),
            )
            records = []
            if job is not None and job.status is ConversionHubJobStatus.SUCCEEDED:
                records = await self._artifacts.list_for_transcript(
                    owner_user_id=actor.id,
                    transcript_id=transcript.id,
                )
            export_state = None
            if job is not None:
                export_state = await self._export_states.get_by_job_id(
                    owner_user_id=actor.id,
                    conversion_hub_job_id=job.id,
                )
        if job is None:
            return ConversionHubTranscriptFormatterExportResponse(
                transcript_id=transcript.id,
                conversion_hub_job_id=None,
                status=ConversionHubTranscriptFormatterExportStatus.NOT_REQUESTED,
                requested_artifacts=[],
                artifacts=[],
            )
        return export_support.response_from_job_and_records(
            transcript_id=transcript.id,
            job=job,
            records=records,
            requested_artifacts=(
                export_state.requested_artifacts if export_state is not None else None
            ),
        )


async def _load_transcript(
    *,
    transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
    actor: User,
    transcript_id: UUID,
) -> ConversionHubSavedTranscript:
    transcript = await transcripts.get_by_owner_and_id(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    if transcript is None:
        raise not_found("ConversionHubSavedTranscript", str(transcript_id))
    return transcript


def _artifact_records(
    *,
    actor: User,
    transcript: ConversionHubSavedTranscript,
    job: ConversionHubJob,
    sir_convert_job_id: str,
    artifact_refs: list[ConversionHubTranscriptFormatterArtifactRef],
    artifact_content: dict[ConversionHubTranscriptFormatterArtifactKey, bytes],
    now: datetime,
    id_generator: IdGeneratorProtocol,
) -> list[ConversionHubTranscriptFormatterArtifactRecord]:
    return [
        ConversionHubTranscriptFormatterArtifactRecord(
            id=id_generator.new_uuid(),
            owner_user_id=actor.id,
            transcript_id=transcript.id,
            conversion_hub_job_id=job.id,
            sir_convert_job_id=sir_convert_job_id,
            requested_artifact=artifact.requested_artifact,
            artifact_key=artifact.artifact_key,
            filename=artifact.filename,
            content_type=artifact.content_type,
            size_bytes=artifact.size_bytes,
            sha256=artifact.sha256,
            retrieval_path=artifact.retrieval_path,
            content=artifact_content[artifact.artifact_key],
            created_at=now,
            updated_at=now,
        )
        for artifact in artifact_refs
    ]
