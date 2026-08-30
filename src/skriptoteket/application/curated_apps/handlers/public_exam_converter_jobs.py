"""Application handler for transient public Exam Converter jobs."""

from __future__ import annotations

import json
from datetime import timedelta

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionNamedArtifact,
    ExamConversionStoredArtifact,
)
from skriptoteket.application.curated_apps.exam_conversion_review_artifacts import (
    build_artifact_manifest,
)
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterArtifact,
    PublicExamConverterArtifactManifestResponse,
    PublicExamConverterJobResultResponse,
    PublicExamConverterJobStatus,
    PublicExamConverterJobStatusResponse,
    PublicExamConverterSubmitResponse,
    PublicExamConverterSubmittedJob,
    PublicExamConverterTarget,
    PublicExamConverterUpload,
)
from skriptoteket.application.curated_apps.public_exam_converter_artifacts import (
    project_public_exam_converter_manifest,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_conversion import ExamConversionArtifactStoreProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.public_exam_converter import PublicExamConverterJobStoreProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

APP_ID = "documents.conversion_hub"
CAPABILITY = "exam_converter"


class PublicExamConverterRuntimeHandler:
    """Expose local asynchronous conversion through the stable public contract."""

    def __init__(
        self,
        *,
        store: PublicExamConverterJobStoreProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._store = store
        self._artifacts = artifacts
        self._uow = uow
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
        concurrency_limit: int,
        api_namespace: str,
    ) -> PublicExamConverterSubmitResponse:
        now = self._clock.now()
        local_job_id = self._id_generator.new_uuid()
        public_job_id = str(local_job_id)
        candidate = PublicExamConverterSubmittedJob(
            public_job_id=public_job_id,
            local_job_id=local_job_id,
            requested_targets=targets,
            status=PublicExamConverterJobStatus.QUEUED,
            source_filename=source_dxe.filename,
            submitted_at=now,
            updated_at=now,
            expires_at=now + timedelta(seconds=artifact_ttl_seconds),
            correlation_id=correlation_id,
            source_dxe=source_dxe,
            graded_result_pdf=graded_result_pdf,
        )
        async with self._uow:
            job = await self._store.create_if_capacity(
                job=candidate,
                now=now,
                concurrency_limit=concurrency_limit,
            )
        if job is None:
            raise DomainError(
                code=ErrorCode.TOO_MANY_REQUESTS,
                message="Public Exam Converter concurrency limit exceeded.",
                details={
                    "app_id": APP_ID,
                    "capability": CAPABILITY,
                    "reason_code": "public_exam_converter_concurrency_limited",
                },
            )
        return PublicExamConverterSubmitResponse(
            public_job_id=public_job_id,
            status=job.status,
            requested_targets=list(job.requested_targets),
            artifact_ttl_seconds=artifact_ttl_seconds,
            expires_at=job.expires_at,
            poll_url=f"{api_namespace}/jobs/{public_job_id}",
            result_url=f"{api_namespace}/jobs/{public_job_id}/result",
            artifact_manifest_url=f"{api_namespace}/jobs/{public_job_id}/artifacts",
        )

    async def get_status(
        self,
        *,
        public_job_id: str,
        correlation_id: str,
    ) -> PublicExamConverterJobStatusResponse:
        del correlation_id
        job = await self._load_job(public_job_id=public_job_id)
        return PublicExamConverterJobStatusResponse(
            public_job_id=job.public_job_id,
            status=job.status,
            submitted_at=job.submitted_at,
            updated_at=job.updated_at,
            expires_at=job.expires_at,
            error=job.error_message,
        )

    async def get_result(
        self,
        *,
        public_job_id: str,
        correlation_id: str,
        api_namespace: str,
    ) -> PublicExamConverterJobResultResponse:
        del correlation_id
        job = await self._load_job(public_job_id=public_job_id)
        if job.status is not PublicExamConverterJobStatus.SUCCEEDED:
            return PublicExamConverterJobResultResponse(
                public_job_id=job.public_job_id,
                status=job.status,
                expires_at=job.expires_at,
                error=job.error_message,
            )
        return PublicExamConverterJobResultResponse(
            public_job_id=job.public_job_id,
            status=job.status,
            expires_at=job.expires_at,
            result=job.result,
            artifact_manifest_url=f"{api_namespace}/jobs/{public_job_id}/artifacts",
        )

    async def get_artifact_manifest(
        self,
        *,
        public_job_id: str,
        correlation_id: str,
        api_namespace: str,
    ) -> PublicExamConverterArtifactManifestResponse:
        del correlation_id
        job = await self._load_job(public_job_id=public_job_id)
        if job.status is not PublicExamConverterJobStatus.SUCCEEDED:
            return PublicExamConverterArtifactManifestResponse(
                public_job_id=job.public_job_id,
                status=job.status,
                expires_at=job.expires_at,
                artifacts=[],
            )
        artifact = self._artifacts.read_artifact(job_id=job.local_job_id)
        return project_public_exam_converter_manifest(
            public_job_id=job.public_job_id,
            status=job.status,
            expires_at=job.expires_at,
            manifest=_local_manifest(job=job, artifact=artifact),
            api_namespace=api_namespace,
        )

    async def download_artifact(
        self,
        *,
        public_job_id: str,
        artifact_key: str,
        correlation_id: str,
    ) -> PublicExamConverterArtifact:
        del correlation_id
        job = await self._load_job(public_job_id=public_job_id)
        if job.status is not PublicExamConverterJobStatus.SUCCEEDED:
            raise validation_error(
                "Public Exam Converter job has no downloadable artifact yet.",
                details={
                    "app_id": APP_ID,
                    "capability": CAPABILITY,
                    "reason_code": "public_exam_converter_artifact_not_ready",
                    "status": job.status.value,
                },
            )
        artifact = self._artifacts.read_artifact(job_id=job.local_job_id)
        manifest = _local_manifest(job=job, artifact=artifact)
        entries = manifest.get("artifacts")
        available: set[str] = set()
        if isinstance(entries, list):
            available = {
                str(entry.get("artifact_key"))
                for entry in entries
                if isinstance(entry, dict) and entry.get("availability") == "available"
            }
        if artifact_key not in available:
            raise validation_error(
                "Public Exam Converter artifact is not available for download.",
                details={
                    "app_id": APP_ID,
                    "capability": CAPABILITY,
                    "reason_code": "public_exam_converter_artifact_not_available",
                    "artifact_key": artifact_key,
                },
            )
        for named in artifact.named_artifacts:
            if named.artifact_key == artifact_key:
                return PublicExamConverterArtifact(
                    filename=named.filename,
                    content_type=named.content_type,
                    content=named.content,
                )
        raise not_found("PublicExamConverterArtifact", artifact_key)

    async def _load_job(self, *, public_job_id: str) -> PublicExamConverterSubmittedJob:
        async with self._uow:
            job = await self._store.get(public_job_id=public_job_id, now=self._clock.now())
        if job is None:
            raise not_found("PublicExamConverterJob", public_job_id)
        return job


def _local_manifest(
    *,
    job: PublicExamConverterSubmittedJob,
    artifact: ExamConversionStoredArtifact,
) -> dict[str, JsonValue]:
    manifest = build_artifact_manifest(
        job_id=job.local_job_id,
        source_filename=artifact.source_filename,
        source_content=artifact.source_content,
        artifacts=artifact.named_artifacts,
    )
    _project_source_warnings(manifest=manifest, artifacts=artifact.named_artifacts)
    requested = {target.value for target in job.requested_targets}
    readiness = manifest.get("readiness")
    exportable: set[str] = set()
    if isinstance(readiness, dict):
        values = readiness.get("exportable_targets")
        if isinstance(values, list):
            exportable = {value for value in values if isinstance(value, str)}
    entries = manifest.get("artifacts")
    if not isinstance(entries, list):
        return manifest
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = entry.get("artifact_key")
        target = key if key in {"examnet_pdf", "qti_package"} else None
        if key == "qti_validation_report":
            target = "qti_package"
        if not isinstance(target, str):
            continue
        if target not in requested:
            _mark_unavailable(entry=entry, availability="not_requested", code=None)
        elif target not in exportable:
            _mark_unavailable(
                entry=entry,
                availability="unavailable",
                code="manual_answer_key_required",
            )
    return manifest


def _project_source_warnings(
    *,
    manifest: dict[str, JsonValue],
    artifacts: tuple[ExamConversionNamedArtifact, ...],
) -> None:
    source_ir = next(
        (artifact for artifact in artifacts if artifact.artifact_key == "source_ir_json"),
        None,
    )
    if source_ir is None:
        return
    decoded = json.loads(source_ir.content)
    if not isinstance(decoded, dict):
        return
    warnings = decoded.get("warnings")
    if not isinstance(warnings, list) or not warnings:
        return
    manifest["warnings"] = {"count": len(warnings), "items": warnings}


def _mark_unavailable(
    *,
    entry: dict[str, JsonValue],
    availability: str,
    code: str | None,
) -> None:
    entry["availability"] = availability
    entry["size_bytes"] = None
    entry["sha256"] = None
    entry["download_path"] = None
    entry["unavailable_code"] = code
