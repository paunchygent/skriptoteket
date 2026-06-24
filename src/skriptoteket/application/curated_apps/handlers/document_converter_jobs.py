"""Document Converter batch submission handler.

Purpose:
    Create owner-scoped local jobs for route-inactive Document Converter batch
    requests and automatically route each validated item to either local
    app-boundary conversion or Sir Convert producer work.

Relationships:
    Reuses the Conversion Hub local job ledger, Sir Convert client protocol,
    shared document processing protocols, and local artifact store while
    keeping FastAPI multipart details outside the application layer.
"""

from __future__ import annotations

import logging

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterProducerDecision,
    DocumentConverterProducerKind,
    DocumentConverterSubmitResult,
    DocumentConverterSubmittedJob,
    build_local_document_converter_producer_id,
)
from skriptoteket.application.curated_apps.document_converter_producers import (
    DocumentConverterProducerPolicy,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
    JobSpecBuilder,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.document_converter import (
    DocumentConverterArtifactStoreProtocol,
    LocalDocumentConverterProducerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertSubmitRequestV2,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_SUBMIT_FAILURE_MESSAGE = "Kunde inte starta konverteringen just nu. Försök igen."
_LOCAL_ARTIFACT_FAILURE_MESSAGE = "Kunde inte spara konverteringsresultatet just nu."

logger = logging.getLogger(__name__)


class CreateDocumentConverterJobsHandler:
    """Create local Document Converter jobs with automatic producer routing."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        policy: DocumentConverterProducerPolicy,
        local_producer: LocalDocumentConverterProducerProtocol,
        local_artifacts: DocumentConverterArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._client = client
        self._policy = policy
        self._local_producer = local_producer
        self._local_artifacts = local_artifacts
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        spec: ConversionHubJobSpecV2,
        uploads: list[ConversionHubUpload],
        wait_seconds: int,
        correlation_id: str | None,
        build_job_spec: JobSpecBuilder,
    ) -> DocumentConverterSubmitResult:
        """Create and route a validated Document Converter batch.

        Args:
            actor: Authenticated owner of the batch request.
            spec: Validated route shared by all batch items.
            uploads: Validated upload payloads.
            wait_seconds: Optional upstream wait budget for Sir Convert paths.
            correlation_id: Request correlation id.
            build_job_spec: Builder for Sir Convert v2 job specs when selected.

        Returns:
            Local job ids plus producer decisions for every item.
        """
        submitted_jobs: list[DocumentConverterSubmittedJob] = []
        for upload in uploads:
            decision = await self._policy.decide(
                spec=spec,
                upload=upload,
                correlation_id=correlation_id,
            )
            local_job = await self._create_local_job(
                actor=actor,
                spec=spec,
                filename=upload.filename,
                correlation_id=correlation_id,
            )
            if decision.producer is DocumentConverterProducerKind.LOCAL:
                job = await self._complete_local_job(
                    job=local_job,
                    spec=spec,
                    upload=upload,
                    decision=decision,
                    correlation_id=correlation_id,
                )
            else:
                job = await self._submit_sir_convert_job(
                    job=local_job,
                    spec=spec,
                    upload=upload,
                    decision=decision,
                    wait_seconds=wait_seconds,
                    correlation_id=correlation_id,
                    build_job_spec=build_job_spec,
                )
            submitted_jobs.append(self._to_submitted_job(job=job, decision=decision))
        return DocumentConverterSubmitResult(jobs=submitted_jobs)

    async def _create_local_job(
        self,
        *,
        actor: User,
        spec: ConversionHubJobSpecV2,
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
                    source_format=spec.source_format,
                    output_format=spec.output_format,
                    pdf_layout=spec.pdf_layout,
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
        spec: ConversionHubJobSpecV2,
        upload: ConversionHubUpload,
        decision: DocumentConverterProducerDecision,
        correlation_id: str | None,
    ) -> ConversionHubJob:
        del decision
        try:
            artifact = await self._local_producer.convert(
                spec=spec,
                upload=upload,
                correlation_id=correlation_id,
            )
            self._local_artifacts.store_artifact(job_id=job.id, artifact=artifact)
        except DomainError as exc:
            return await self._update_job(
                job=job,
                status=ConversionHubJobStatus.FAILED,
                error_message=exc.message,
            )
        except Exception as exc:
            logger.warning(
                "Document Converter local artifact completion failed",
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
            upstream_job_id=build_local_document_converter_producer_id(job_id=job.id),
            error_message=None,
        )

    async def _submit_sir_convert_job(
        self,
        *,
        job: ConversionHubJob,
        spec: ConversionHubJobSpecV2,
        upload: ConversionHubUpload,
        decision: DocumentConverterProducerDecision,
        wait_seconds: int,
        correlation_id: str | None,
        build_job_spec: JobSpecBuilder,
    ) -> ConversionHubJob:
        del decision
        try:
            submitted = await self._client.submit_job(
                request=SirConvertSubmitRequestV2(
                    filename=upload.filename,
                    content_type=upload.content_type,
                    file_bytes=upload.file_bytes,
                    job_spec=build_job_spec(spec=spec, filename=upload.filename),
                    idempotency_key=str(job.id),
                    wait_seconds=wait_seconds,
                    correlation_id=correlation_id,
                )
            )
        except DomainError:
            return await self._update_job(
                job=job,
                status=ConversionHubJobStatus.FAILED,
                error_message=_SUBMIT_FAILURE_MESSAGE,
            )

        return await self._update_job(
            job=job,
            status=ConversionHubJobStatus.from_upstream(submitted.status),
            upstream_job_id=submitted.job_id,
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

    def _to_submitted_job(
        self,
        *,
        job: ConversionHubJob,
        decision: DocumentConverterProducerDecision,
    ) -> DocumentConverterSubmittedJob:
        return DocumentConverterSubmittedJob(
            input_filename=job.input_filename,
            job_id=job.id,
            status=job.status,
            error=job.error_message,
            producer=decision.producer,
            producer_reason=decision.reason,
        )
