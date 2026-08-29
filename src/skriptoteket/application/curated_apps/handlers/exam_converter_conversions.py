"""In-process Exam Converter conversion handler.

Purpose:
    Create the owner-scoped local job for one authenticated in-process
    dxe -> Exam.net bundle conversion, produce the bundle inside the
    Skriptoteket app boundary, and persist it for the existing Conversion Hub
    artifact download surface.

Relationships:
    Reuses the Conversion Hub local job ledger and the in-process Exam
    Converter producer/artifact-store protocols. The lane switch defaults to
    the Sir Convert-backed path, which keeps this handler inert until an
    operator enables the in-process lane.
"""

from __future__ import annotations

import logging

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    enqueue_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConverterConversionLane,
    ExamConverterConversionSubmitResult,
    build_local_exam_conversion_producer_id,
)
from skriptoteket.application.curated_apps.exam_conversion_producers import parse_source_exam
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    AnswerKeyEnrichmentPlanState,
    plan_answer_key_enrichment,
)
from skriptoteket.domain.errors import DomainError, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.exam_conversion import (
    ExamConversionArtifactStoreProtocol,
    InProcessExamConverterProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_LANE_DISABLED_MESSAGE = "Den inbyggda provkonverteringen är inte aktiverad."
_LOCAL_ARTIFACT_FAILURE_MESSAGE = "Kunde inte spara konverteringsresultatet just nu."

logger = logging.getLogger(__name__)


class CreateExamConverterConversionJobsHandler:
    """Create one local in-process Exam Converter conversion job."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        lane: ExamConverterConversionLane,
        producer: InProcessExamConverterProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        enrichment_enabled: bool,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._lane = lane
        self._producer = producer
        self._artifacts = artifacts
        self._enrichment_jobs = enrichment_jobs
        self._enrichment_enabled = enrichment_enabled
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        upload: ConversionHubUpload,
        overlay_bytes: bytes | None,
        correlation_id: str | None,
    ) -> ExamConverterConversionSubmitResult:
        """Convert one uploaded `.dxe` export through the in-process lane.

        Args:
            actor: Authenticated owner of the conversion.
            upload: Uploaded `.dxe` payload.
            overlay_bytes: Optional source-bound teacher ingestion overlay.
            correlation_id: Request correlation id.

        Returns:
            The locally owned job id plus terminal conversion status.

        Raises:
            DomainError: If the in-process lane is not enabled.
        """
        if self._lane.value != "in_process":
            raise validation_error(_LANE_DISABLED_MESSAGE)
        if self._should_enqueue_enrichment(upload=upload, overlay_bytes=overlay_bytes):
            job = await self._create_job_with_enrichment(
                actor=actor,
                upload=upload,
                correlation_id=correlation_id,
            )
            return ExamConverterConversionSubmitResult(
                job_id=job.id,
                status=job.status,
                error=job.error_message,
            )
        job = await self._create_local_job(
            actor=actor,
            filename=upload.filename,
            correlation_id=correlation_id,
        )
        job = await self._complete_local_job(
            job=job,
            upload=upload,
            overlay_bytes=overlay_bytes,
            correlation_id=correlation_id,
        )
        return ExamConverterConversionSubmitResult(
            job_id=job.id,
            status=job.status,
            error=job.error_message,
        )

    def _should_enqueue_enrichment(
        self,
        *,
        upload: ConversionHubUpload,
        overlay_bytes: bytes | None,
    ) -> bool:
        """Route unkeyed, overlay-free exams to the enrichment worker job.

        Source-keyed and overlay-keyed uploads keep the unchanged synchronous
        ST-SKRIPT-39-01 path; so does every upload when the answer-key lane is
        disabled or the exam has blockers machine proposals cannot clear.
        """
        if not self._enrichment_enabled or overlay_bytes is not None:
            return False
        try:
            exam = parse_source_exam(upload=upload)
        except DomainError:
            return False
        plan = plan_answer_key_enrichment(exam)
        return plan.state is AnswerKeyEnrichmentPlanState.ELIGIBLE

    async def _create_job_with_enrichment(
        self,
        *,
        actor: User,
        upload: ConversionHubUpload,
        correlation_id: str | None,
    ) -> ConversionHubJob:
        now = self._clock.now()
        async with self._uow:
            job = await self._jobs.create(
                job=ConversionHubJob(
                    id=self._id_generator.new_uuid(),
                    owner_user_id=actor.id,
                    input_filename=upload.filename,
                    source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
                    output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
                    pdf_layout=None,
                    status=ConversionHubJobStatus.SUBMITTED,
                    correlation_id=correlation_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            await self._enrichment_jobs.create(
                job=enqueue_enrichment_job(
                    job_id=self._id_generator.new_uuid(),
                    conversion_job_id=job.id,
                    owner_user_id=actor.id,
                    input_filename=upload.filename,
                    source_dxe=upload.file_bytes,
                    now=now,
                )
            )
        return job

    async def _create_local_job(
        self,
        *,
        actor: User,
        filename: str,
        correlation_id: str | None,
    ) -> ConversionHubJob:
        now = self._clock.now()
        async with self._uow:
            return await self._jobs.create(
                job=ConversionHubJob(
                    id=self._id_generator.new_uuid(),
                    owner_user_id=actor.id,
                    input_filename=filename,
                    source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
                    output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
                    pdf_layout=None,
                    status=ConversionHubJobStatus.SUBMITTED,
                    correlation_id=correlation_id,
                    created_at=now,
                    updated_at=now,
                )
            )

    async def _complete_local_job(
        self,
        *,
        job: ConversionHubJob,
        upload: ConversionHubUpload,
        overlay_bytes: bytes | None,
        correlation_id: str | None,
    ) -> ConversionHubJob:
        try:
            artifact = await self._producer.convert(
                upload=upload,
                overlay_bytes=overlay_bytes,
                correlation_id=correlation_id,
            )
            self._artifacts.store_artifact(job_id=job.id, artifact=artifact)
        except DomainError as exc:
            return await self._update_job(
                job=job,
                status=ConversionHubJobStatus.FAILED,
                error_message=exc.message,
            )
        except Exception as exc:
            logger.warning(
                "Exam Converter in-process conversion failed",
                extra={
                    "job_id": str(job.id),
                    "error_type": type(exc).__name__,
                },
            )
            return await self._update_job(
                job=job,
                status=ConversionHubJobStatus.FAILED,
                error_message=_LOCAL_ARTIFACT_FAILURE_MESSAGE,
            )

        return await self._update_job(
            job=job,
            status=ConversionHubJobStatus.SUCCEEDED,
            upstream_job_id=build_local_exam_conversion_producer_id(job_id=job.id),
            error_message=None,
        )

    async def _update_job(
        self,
        *,
        job: ConversionHubJob,
        status: ConversionHubJobStatus,
        upstream_job_id: str | None = None,
        error_message: str | None = None,
    ) -> ConversionHubJob:
        async with self._uow:
            return await self._jobs.update(
                job=job.model_copy(
                    update={
                        "upstream_job_id": upstream_job_id or job.upstream_job_id,
                        "status": status,
                        "error_message": error_message,
                        "updated_at": self._clock.now(),
                    }
                )
            )
