"""Application handler for public Exam Converter jobs.

Purpose:
  Orchestrate anonymous public Exam Converter submission, polling, manifest
  projection, and named artifact download through server-side grant/upstream
  seams while preserving only transient local job state.

Relationships:
  - Uses HuleEdu public grant authority through
    `PublicExamConverterGrantAuthorityProtocol`.
  - Uses Sir Convert-a-Lot v2 through `SirConvertALotClientV2Protocol`.
  - Called by `web/api/v1/public_apps_exam_converter.py`.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import timedelta

from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterArtifactManifestResponse,
    PublicExamConverterArtifactReadLease,
    PublicExamConverterJobResultResponse,
    PublicExamConverterJobStatus,
    PublicExamConverterJobStatusResponse,
    PublicExamConverterSubmitResponse,
    PublicExamConverterSubmittedJob,
    PublicExamConverterTarget,
    PublicExamConverterUpload,
)
from skriptoteket.application.curated_apps.public_exam_converter_artifacts import (
    artifact_read_lease_for_key,
    artifact_read_leases_from_manifest,
    project_public_exam_converter_manifest,
    upload_mime_types,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.public_exam_converter import (
    PublicExamConverterGrantAuthorityProtocol,
    PublicExamConverterGrantRequest,
    PublicExamConverterJobStoreProtocol,
    PublicExamConverterSirConvertProtocol,
    PublicExamConverterSirConvertSubmitRequest,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactV2,
)

APP_ID = "documents.conversion_hub"
CAPABILITY = "exam_converter"
ROUTE_KEY = "digiexam_dxe_to_examnet_migration_bundle"
_TERMINAL_STATUSES = frozenset(
    {
        PublicExamConverterJobStatus.SUCCEEDED,
        PublicExamConverterJobStatus.FAILED,
        PublicExamConverterJobStatus.CANCELED,
        PublicExamConverterJobStatus.EXPIRED,
    }
)


class PublicExamConverterRuntimeHandler:
    """Handle the public one-time Exam Converter runtime flow."""

    def __init__(
        self,
        *,
        store: PublicExamConverterJobStoreProtocol,
        grant_authority: PublicExamConverterGrantAuthorityProtocol,
        sir_convert: PublicExamConverterSirConvertProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._store = store
        self._grant_authority = grant_authority
        self._sir_convert = sir_convert
        self._clock = clock
        self._id_generator = id_generator

    async def submit(
        self,
        *,
        source_dxe: PublicExamConverterUpload,
        graded_result_pdf: PublicExamConverterUpload | None,
        targets: tuple[PublicExamConverterTarget, ...],
        correlation_id: str,
        artifact_ttl_seconds: int,
        api_namespace: str,
    ) -> PublicExamConverterSubmitResponse:
        now = self._clock.now()
        public_job_id = str(self._id_generator.new_uuid())
        aggregate_bytes = len(source_dxe.file_bytes) + len(
            graded_result_pdf.file_bytes if graded_result_pdf is not None else b""
        )
        upload_digest = _upload_digest(
            source_dxe=source_dxe,
            graded_result_pdf=graded_result_pdf,
            targets=targets,
        )
        grant = await self._grant_authority.mint_conversion_grant(
            request=PublicExamConverterGrantRequest(
                upload_digest=upload_digest,
                aggregate_upload_bytes=aggregate_bytes,
                upload_mime_types=upload_mime_types(
                    source_dxe=source_dxe,
                    graded_result_pdf=graded_result_pdf,
                ),
                allowed_targets=targets,
                correlation_id=correlation_id,
            )
        )
        upstream = await self._sir_convert.submit_public_exam_converter_job(
            request=PublicExamConverterSirConvertSubmitRequest(
                filename=source_dxe.filename,
                content_type=source_dxe.content_type,
                file_bytes=source_dxe.file_bytes,
                job_spec=_build_job_spec(
                    source_dxe=source_dxe,
                    graded_result_pdf=graded_result_pdf,
                    targets=targets,
                ),
                idempotency_key=public_job_id,
                wait_seconds=0,
                correlation_id=correlation_id,
                public_conversion_grant=grant.token,
                graded_result_pdf_filename=(
                    graded_result_pdf.filename if graded_result_pdf is not None else None
                ),
                graded_result_pdf_bytes=(
                    graded_result_pdf.file_bytes if graded_result_pdf is not None else None
                ),
            )
        )
        status = PublicExamConverterJobStatus.from_upstream(upstream.status)
        ttl_seconds = min(artifact_ttl_seconds, grant.artifact_ttl_seconds)
        expires_at = min(grant.expires_at, now + timedelta(seconds=ttl_seconds))
        job = await self._store.create(
            job=PublicExamConverterSubmittedJob(
                public_job_id=public_job_id,
                upstream_job_id=upstream.job_id,
                grant_token=grant.token,
                manifest_artifact_read_lease_token=(upstream.manifest_artifact_read_lease_token),
                requested_targets=targets,
                status=status,
                source_filename=source_dxe.filename,
                submitted_at=now,
                updated_at=now,
                expires_at=expires_at,
                correlation_id=correlation_id,
            )
        )
        return PublicExamConverterSubmitResponse(
            public_job_id=public_job_id,
            status=job.status,
            requested_targets=list(job.requested_targets),
            artifact_ttl_seconds=ttl_seconds,
            expires_at=job.expires_at,
            poll_url=f"{api_namespace}/jobs/{public_job_id}",
            result_url=f"{api_namespace}/jobs/{public_job_id}/result",
            artifact_manifest_url=f"{api_namespace}/jobs/{public_job_id}/artifacts",
        )

    async def count_active_jobs(self) -> int:
        return await self._store.count_active(now=self._clock.now())

    async def get_status(
        self,
        *,
        public_job_id: str,
        correlation_id: str,
    ) -> PublicExamConverterJobStatusResponse:
        job = await self._load_job(public_job_id=public_job_id)
        refreshed = await self._refresh_job(job=job, correlation_id=correlation_id)
        return PublicExamConverterJobStatusResponse(
            public_job_id=refreshed.public_job_id,
            status=refreshed.status,
            submitted_at=refreshed.submitted_at,
            updated_at=refreshed.updated_at,
            expires_at=refreshed.expires_at,
            error=refreshed.error_message,
        )

    async def get_result(
        self,
        *,
        public_job_id: str,
        correlation_id: str,
        api_namespace: str,
    ) -> PublicExamConverterJobResultResponse:
        job = await self._load_job(public_job_id=public_job_id)
        refreshed = await self._refresh_job(job=job, correlation_id=correlation_id)
        if refreshed.status is not PublicExamConverterJobStatus.SUCCEEDED:
            return PublicExamConverterJobResultResponse(
                public_job_id=refreshed.public_job_id,
                status=refreshed.status,
                expires_at=refreshed.expires_at,
                error=refreshed.error_message,
            )
        result = await self._sir_convert.get_public_exam_converter_result(
            refreshed.upstream_job_id,
            public_conversion_grant=refreshed.grant_token,
            correlation_id=correlation_id,
        )
        return PublicExamConverterJobResultResponse(
            public_job_id=refreshed.public_job_id,
            status=refreshed.status,
            expires_at=refreshed.expires_at,
            result=result.get("result") if isinstance(result.get("result"), dict) else result,
            artifact_manifest_url=f"{api_namespace}/jobs/{public_job_id}/artifacts",
        )

    async def get_artifact_manifest(
        self,
        *,
        public_job_id: str,
        correlation_id: str,
        api_namespace: str,
    ) -> PublicExamConverterArtifactManifestResponse:
        job = await self._load_job(public_job_id=public_job_id)
        refreshed = await self._refresh_job(job=job, correlation_id=correlation_id)
        if refreshed.status is not PublicExamConverterJobStatus.SUCCEEDED:
            return PublicExamConverterArtifactManifestResponse(
                public_job_id=refreshed.public_job_id,
                status=refreshed.status,
                expires_at=refreshed.expires_at,
                artifacts=[],
            )
        manifest = await self._sir_convert.get_public_exam_converter_artifact_manifest(
            refreshed.upstream_job_id,
            public_conversion_grant=refreshed.grant_token,
            public_artifact_read_lease=refreshed.manifest_artifact_read_lease_token,
            correlation_id=correlation_id,
        )
        refreshed = await self._store_artifact_read_leases(job=refreshed, manifest=manifest)
        return project_public_exam_converter_manifest(
            public_job_id=refreshed.public_job_id,
            status=refreshed.status,
            expires_at=refreshed.expires_at,
            manifest=manifest,
            api_namespace=api_namespace,
        )

    async def download_artifact(
        self,
        *,
        public_job_id: str,
        artifact_key: str,
        correlation_id: str,
    ) -> SirConvertArtifactV2:
        job = await self._load_job(public_job_id=public_job_id)
        refreshed = await self._refresh_job(job=job, correlation_id=correlation_id)
        if refreshed.status is not PublicExamConverterJobStatus.SUCCEEDED:
            raise validation_error(
                "Public Exam Converter job has no downloadable artifact yet.",
                details={
                    "app_id": APP_ID,
                    "capability": CAPABILITY,
                    "reason_code": "public_exam_converter_artifact_not_ready",
                    "status": refreshed.status.value,
                },
            )
        artifact_read_lease = await self._artifact_read_lease_for_download(
            job=refreshed,
            artifact_key=artifact_key,
            correlation_id=correlation_id,
        )
        return await self._sir_convert.download_public_exam_converter_artifact(
            refreshed.upstream_job_id,
            artifact_key=artifact_key,
            public_conversion_grant=refreshed.grant_token,
            public_artifact_read_lease=artifact_read_lease.token,
            correlation_id=correlation_id,
        )

    async def _load_job(self, *, public_job_id: str) -> PublicExamConverterSubmittedJob:
        job = await self._store.get(public_job_id=public_job_id, now=self._clock.now())
        if job is None:
            raise not_found("PublicExamConverterJob", public_job_id)
        return job

    async def _refresh_job(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        correlation_id: str,
    ) -> PublicExamConverterSubmittedJob:
        if job.status in _TERMINAL_STATUSES:
            return job
        try:
            upstream = await self._sir_convert.get_public_exam_converter_job(
                job.upstream_job_id,
                public_conversion_grant=job.grant_token,
                correlation_id=correlation_id,
            )
        except DomainError as exc:
            failed = replace(
                job,
                status=PublicExamConverterJobStatus.FAILED,
                updated_at=self._clock.now(),
                error_message="Public Exam Converter upstream status check failed.",
            )
            await self._store.update(job=failed)
            raise _upstream_error(exc) from exc

        status = PublicExamConverterJobStatus.from_upstream(upstream.status)
        if status is job.status:
            return job
        updated = replace(
            job,
            status=status,
            updated_at=self._clock.now(),
            error_message="Public Exam Converter upstream job failed."
            if status is PublicExamConverterJobStatus.FAILED
            else None,
        )
        return await self._store.update(job=updated)

    async def _store_artifact_read_leases(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        manifest: dict[str, object],
    ) -> PublicExamConverterSubmittedJob:
        leases = artifact_read_leases_from_manifest(manifest)
        if not leases:
            return job
        updated = replace(job, artifact_read_leases=leases)
        return await self._store.update(job=updated)

    async def _artifact_read_lease_for_download(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        artifact_key: str,
        correlation_id: str,
    ) -> PublicExamConverterArtifactReadLease:
        lease = artifact_read_lease_for_key(job=job, artifact_key=artifact_key)
        if lease is not None:
            return lease
        manifest = await self._sir_convert.get_public_exam_converter_artifact_manifest(
            job.upstream_job_id,
            public_conversion_grant=job.grant_token,
            public_artifact_read_lease=job.manifest_artifact_read_lease_token,
            correlation_id=correlation_id,
        )
        refreshed = await self._store_artifact_read_leases(job=job, manifest=manifest)
        lease = artifact_read_lease_for_key(job=refreshed, artifact_key=artifact_key)
        if lease is not None:
            return lease
        raise validation_error(
            "Public Exam Converter artifact is not available for download.",
            details={
                "app_id": APP_ID,
                "capability": CAPABILITY,
                "reason_code": "public_exam_converter_artifact_not_available",
                "artifact_key": artifact_key,
            },
        )


def _build_job_spec(
    *,
    source_dxe: PublicExamConverterUpload,
    graded_result_pdf: PublicExamConverterUpload | None,
    targets: tuple[PublicExamConverterTarget, ...],
) -> dict[str, object]:
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": source_dxe.filename, "format": "digiexam_dxe"},
        "conversion": {
            "output_format": "examnet_migration_bundle",
            "targets": [target.value for target in targets],
            "artifact_language": "sv",
            "reference_docx_filename": None,
        },
        "digiexam_migration_options": {
            "graded_result_pdf_filename": (
                graded_result_pdf.filename if graded_result_pdf is not None else None
            ),
            "parity_pdf_filename": None,
            "result_pdf_usage": "correct_machine_marked_answers_only",
            "manual_follow_up_policy": "emit_item_addressable_report",
        },
        "retention": {"pin": False},
    }


def _upload_digest(
    *,
    source_dxe: PublicExamConverterUpload,
    graded_result_pdf: PublicExamConverterUpload | None,
    targets: tuple[PublicExamConverterTarget, ...],
) -> str:
    digest = hashlib.sha256()
    digest.update(source_dxe.filename.encode("utf-8"))
    digest.update(source_dxe.file_bytes)
    if graded_result_pdf is not None:
        digest.update(graded_result_pdf.filename.encode("utf-8"))
        digest.update(graded_result_pdf.file_bytes)
    for target in targets:
        digest.update(target.value.encode("ascii"))
    return f"sha256:{digest.hexdigest()}"


def _upstream_error(error: DomainError) -> DomainError:
    details = dict(error.details)
    details.setdefault("reason_code", "public_exam_converter_upstream_unavailable")
    return DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Public Exam Converter upstream is unavailable.",
        details=details,
    )
