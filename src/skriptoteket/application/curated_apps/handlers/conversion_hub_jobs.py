"""Application handlers for locally owned Conversion Hub jobs.

Purpose:
  Orchestrate Conversion Hub job submission, owned status refresh, and artifact
  downloads while keeping Skriptoteket as the source of truth for job identity
  and authorization.

Relationships:
  - Uses `ConversionHubJobRepositoryProtocol` for the local ledger.
  - Uses `SirConvertALotClientV2Protocol` as the upstream conversion engine seam.
  - Returned models are serialized by `web/api/v1/apps_conversion_hub.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
    ConversionHubJobStatusResult,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
    ConversionHubSubmitResult,
    ConversionHubSubmittedJob,
    RegisterExamConverterConversionHubJobRequest,
    RegisterExamConverterConversionHubJobResult,
    RegisterTranscriptConversionHubJobRequest,
    RegisterTranscriptConversionHubJobResult,
)
from skriptoteket.application.curated_apps.exam_conversion import (
    is_local_exam_conversion_job,
)
from skriptoteket.domain.errors import DomainError, not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.exam_conversion import ExamConversionArtifactStoreProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertSubmitRequestV2,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_TERMINAL_STATUSES = frozenset(
    {
        ConversionHubJobStatus.SUCCEEDED,
        ConversionHubJobStatus.FAILED,
        ConversionHubJobStatus.CANCELED,
    }
)
_SUBMIT_FAILURE_MESSAGE = "Kunde inte starta konverteringen just nu. Försök igen."
_UPSTREAM_FAILURE_MESSAGE = "Konverteringen kunde inte slutföras."


class JobSpecBuilder(Protocol):
    """Build the upstream Sir Convert job spec for one uploaded file."""

    def __call__(
        self,
        *,
        spec: ConversionHubJobSpecV2,
        filename: str,
    ) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class ConversionHubUpload:
    """Represent one uploaded file without tying the application layer to FastAPI."""

    filename: str
    content_type: str
    file_bytes: bytes


class CreateConversionHubJobsHandler:
    """Create locally owned Conversion Hub jobs and submit them upstream."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._client = client
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
    ) -> ConversionHubSubmitResult:
        jobs: list[ConversionHubSubmittedJob] = []
        for upload in uploads:
            job_spec = build_job_spec(spec=spec, filename=upload.filename)
            local_job = await self._create_local_job(
                actor=actor,
                spec=spec,
                filename=upload.filename,
                correlation_id=correlation_id,
            )
            try:
                submitted = await self._client.submit_job(
                    request=SirConvertSubmitRequestV2(
                        filename=upload.filename,
                        content_type=upload.content_type,
                        file_bytes=upload.file_bytes,
                        job_spec=job_spec,
                        idempotency_key=str(local_job.id),
                        wait_seconds=wait_seconds,
                        correlation_id=correlation_id,
                    )
                )
            except DomainError:
                failed_job = await self._update_job(
                    job=local_job,
                    status=ConversionHubJobStatus.FAILED,
                    error_message=_SUBMIT_FAILURE_MESSAGE,
                )
                jobs.append(self._to_submitted_job(failed_job))
                continue

            updated_job = await self._update_job(
                job=local_job,
                status=ConversionHubJobStatus.from_sir_convert_status(submitted.status),
                upstream_job_id=submitted.job_id,
                error_message=None,
            )
            jobs.append(self._to_submitted_job(updated_job))
        return ConversionHubSubmitResult(jobs=jobs)

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

    def _to_submitted_job(self, job: ConversionHubJob) -> ConversionHubSubmittedJob:
        return ConversionHubSubmittedJob(
            input_filename=job.input_filename,
            job_id=job.id,
            status=job.status,
            error=job.error_message,
        )


class RegisterExamConverterConversionHubJobHandler:
    """Register a HuleEdu Gateway Exam Converter job in the local job ledger."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        request: RegisterExamConverterConversionHubJobRequest,
    ) -> RegisterExamConverterConversionHubJobResult:
        async with self._uow:
            existing = await self._jobs.get_by_upstream_job_id(
                upstream_job_id=request.upstream_job_id
            )
            if existing is not None:
                if existing.owner_user_id != actor.id:
                    raise not_found("ConversionHubJob", request.upstream_job_id)
                return self._to_result(
                    await self._synchronize_existing_job(job=existing, request=request)
                )

            now = self._clock.now()
            job = await self._jobs.create(
                job=ConversionHubJob(
                    id=self._id_generator.new_uuid(),
                    owner_user_id=actor.id,
                    input_filename=request.input_filename,
                    source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
                    output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
                    pdf_layout=None,
                    upstream_job_id=request.upstream_job_id,
                    status=request.status,
                    correlation_id=request.correlation_id,
                    error_message=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            return self._to_result(job)

    async def _synchronize_existing_job(
        self,
        *,
        job: ConversionHubJob,
        request: RegisterExamConverterConversionHubJobRequest,
    ) -> ConversionHubJob:
        next_status = request.status
        if job.status in _TERMINAL_STATUSES and next_status not in _TERMINAL_STATUSES:
            next_status = job.status
        if (
            job.status is next_status
            and job.input_filename == request.input_filename
            and job.correlation_id == request.correlation_id
        ):
            return job

        return await self._jobs.update(
            job=job.model_copy(
                update={
                    "correlation_id": request.correlation_id,
                    "error_message": None,
                    "input_filename": request.input_filename,
                    "status": next_status,
                    "updated_at": self._clock.now(),
                }
            )
        )

    def _to_result(self, job: ConversionHubJob) -> RegisterExamConverterConversionHubJobResult:
        if job.upstream_job_id is None:
            raise validation_error("Exam Converter job is missing upstream identity.")
        return RegisterExamConverterConversionHubJobResult(
            job_id=job.id,
            upstream_job_id=job.upstream_job_id,
            status=job.status,
        )


class RegisterTranscriptConversionHubJobHandler:
    """Register a HuleEdu Gateway transcript job in the local job ledger."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        request: RegisterTranscriptConversionHubJobRequest,
    ) -> RegisterTranscriptConversionHubJobResult:
        async with self._uow:
            existing = await self._jobs.get_by_upstream_job_id(
                upstream_job_id=request.upstream_job_id
            )
            if existing is not None:
                if existing.owner_user_id != actor.id:
                    raise not_found("ConversionHubJob", request.upstream_job_id)
                return self._to_result(
                    await self._synchronize_existing_job(job=existing, request=request)
                )

            now = self._clock.now()
            job = await self._jobs.create(
                job=ConversionHubJob(
                    id=self._id_generator.new_uuid(),
                    owner_user_id=actor.id,
                    input_filename=request.input_filename,
                    source_format=ConversionHubSourceFormatV2.AUDIO,
                    output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
                    pdf_layout=None,
                    upstream_job_id=request.upstream_job_id,
                    status=request.status,
                    correlation_id=request.correlation_id,
                    error_message=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            return self._to_result(job)

    async def _synchronize_existing_job(
        self,
        *,
        job: ConversionHubJob,
        request: RegisterTranscriptConversionHubJobRequest,
    ) -> ConversionHubJob:
        next_status = request.status
        if job.status in _TERMINAL_STATUSES and next_status not in _TERMINAL_STATUSES:
            next_status = job.status
        if (
            job.status is next_status
            and job.input_filename == request.input_filename
            and job.correlation_id == request.correlation_id
        ):
            return job
        return await self._jobs.update(
            job=job.model_copy(
                update={
                    "correlation_id": request.correlation_id,
                    "error_message": None,
                    "input_filename": request.input_filename,
                    "status": next_status,
                    "updated_at": self._clock.now(),
                }
            )
        )

    def _to_result(self, job: ConversionHubJob) -> RegisterTranscriptConversionHubJobResult:
        if job.upstream_job_id is None:
            raise validation_error("Transcript job is missing upstream identity.")
        return RegisterTranscriptConversionHubJobResult(
            job_id=job.id,
            upstream_job_id=job.upstream_job_id,
            status=job.status,
        )


class _BaseConversionHubJobHandler:
    """Shared owner-loading and upstream-refresh behavior for Conversion Hub jobs."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._jobs = jobs
        self._client = client
        self._uow = uow
        self._clock = clock

    async def _load_owned_job(self, *, actor: User, job_id: UUID) -> ConversionHubJob:
        async with self._uow:
            job = await self._jobs.get_by_id(job_id=job_id)
        if job is None or job.owner_user_id != actor.id:
            raise not_found("ConversionHubJob", str(job_id))
        return job

    async def _refresh_job(
        self,
        *,
        job: ConversionHubJob,
        correlation_id: str | None,
    ) -> ConversionHubJob:
        if job.status in _TERMINAL_STATUSES or job.upstream_job_id is None:
            return job

        upstream = await self._client.get_job(job.upstream_job_id, correlation_id=correlation_id)
        refreshed_status = ConversionHubJobStatus.from_sir_convert_status(upstream.status)
        if refreshed_status is job.status:
            return job

        error_message = None
        if refreshed_status is ConversionHubJobStatus.FAILED:
            error_message = _UPSTREAM_FAILURE_MESSAGE

        async with self._uow:
            return await self._jobs.update(
                job=job.model_copy(
                    update={
                        "status": refreshed_status,
                        "error_message": error_message,
                        "updated_at": self._clock.now(),
                    }
                )
            )


class GetConversionHubJobHandler(_BaseConversionHubJobHandler):
    """Load one locally owned Conversion Hub job."""

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
    ) -> ConversionHubJobStatusResult:
        job = await self._load_owned_job(actor=actor, job_id=job_id)
        refreshed = await self._refresh_job(job=job, correlation_id=correlation_id)
        return ConversionHubJobStatusResult(
            job_id=refreshed.id,
            status=refreshed.status,
            error=refreshed.error_message,
        )


class DownloadConversionHubArtifactHandler(_BaseConversionHubJobHandler):
    """Authorize and proxy one Conversion Hub artifact download."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        exam_artifacts: ExamConversionArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        super().__init__(jobs=jobs, client=client, uow=uow, clock=clock)
        self._exam_artifacts = exam_artifacts

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
    ) -> tuple[str, str, bytes]:
        job = await self._load_owned_job(actor=actor, job_id=job_id)
        refreshed = await self._refresh_job(job=job, correlation_id=correlation_id)

        if refreshed.status is not ConversionHubJobStatus.SUCCEEDED:
            if refreshed.status is ConversionHubJobStatus.FAILED:
                raise validation_error(refreshed.error_message or _UPSTREAM_FAILURE_MESSAGE)
            if refreshed.status is ConversionHubJobStatus.CANCELED:
                raise validation_error("Konverteringen avbröts innan filen blev klar.")
            raise validation_error("Konverteringen är inte klar ännu.")
        if refreshed.upstream_job_id is None:
            raise validation_error("Konverteringen saknar nedladdningsbar artefakt.")

        if is_local_exam_conversion_job(refreshed):
            local_artifact = self._exam_artifacts.read_artifact(job_id=refreshed.id)
            return (
                local_artifact.filename,
                local_artifact.content_type,
                local_artifact.content,
            )

        artifact = await self._client.download_artifact(
            refreshed.upstream_job_id,
            correlation_id=correlation_id,
        )
        return (
            artifact.artifact.filename,
            artifact.artifact.content_type,
            artifact.artifact.content,
        )
