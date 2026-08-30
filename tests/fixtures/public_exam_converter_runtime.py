"""Focused persistence and artifact fixtures for public Exam Converter tests."""

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID

from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionNamedArtifact,
    ExamConversionStoredArtifact,
)
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterJobStatus,
    PublicExamConverterSubmittedJob,
    PublicExamConverterUpload,
)
from skriptoteket.domain.errors import not_found


class FakeUnitOfWork:
    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakePublicExamConverterJobRepository:
    """Deterministic fake for application and route tests."""

    def __init__(self) -> None:
        self.jobs: dict[UUID, PublicExamConverterSubmittedJob] = {}

    async def create_if_capacity(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        now: datetime,
        concurrency_limit: int,
    ) -> PublicExamConverterSubmittedJob | None:
        active = sum(
            1
            for existing in self.jobs.values()
            if existing.expires_at > now
            and existing.status
            in {PublicExamConverterJobStatus.QUEUED, PublicExamConverterJobStatus.PROCESSING}
        )
        if active >= concurrency_limit:
            return None
        self.jobs[job.local_job_id] = job
        return job

    async def get(
        self,
        *,
        public_job_id: str,
        now: datetime,
    ) -> PublicExamConverterSubmittedJob | None:
        try:
            job = self.jobs.get(UUID(public_job_id))
        except ValueError:
            return None
        return job if job is not None and job.expires_at > now else None

    async def update(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        expected_worker_id: str | None = None,
    ) -> PublicExamConverterSubmittedJob:
        current = self.jobs.get(job.local_job_id)
        if (
            expected_worker_id is not None
            and current is not None
            and current.locked_by != expected_worker_id
        ):
            raise AssertionError("worker lease is no longer owned")
        self.jobs[job.local_job_id] = job
        return job

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> PublicExamConverterSubmittedJob | None:
        queued = next(
            (
                job
                for job in self.jobs.values()
                if job.status is PublicExamConverterJobStatus.QUEUED and job.expires_at > now
            ),
            None,
        )
        if queued is None:
            return None
        claimed = replace(
            queued,
            status=PublicExamConverterJobStatus.PROCESSING,
            locked_by=worker_id,
            locked_until=now + lease_ttl,
            updated_at=now,
        )
        return await self.update(job=claimed)

    async def claim_next_expired(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> PublicExamConverterSubmittedJob | None:
        expired = next(
            (
                job
                for job in self.jobs.values()
                if job.status is PublicExamConverterJobStatus.PROCESSING
                and job.locked_until is not None
                and job.locked_until < now
            ),
            None,
        )
        if expired is None:
            return None
        claimed = replace(
            expired,
            locked_by=worker_id,
            locked_until=now + lease_ttl,
            updated_at=now,
        )
        return await self.update(job=claimed)

    async def heartbeat(
        self,
        *,
        local_job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool:
        job = self.jobs.get(local_job_id)
        if job is None or job.locked_by != worker_id:
            return False
        await self.update(job=replace(job, locked_until=now + lease_ttl, updated_at=now))
        return True

    async def delete_next_expired(self, *, now: datetime) -> UUID | None:
        expired_id = next(
            (job_id for job_id, job in self.jobs.items() if job.expires_at <= now),
            None,
        )
        if expired_id is not None:
            del self.jobs[expired_id]
        return expired_id


class FakeExamConversionArtifactStore:
    def __init__(self) -> None:
        self.artifacts: dict[UUID, ExamConversionStoredArtifact] = {}

    def store_artifact(self, *, job_id: UUID, artifact: ExamConversionStoredArtifact) -> None:
        self.artifacts[job_id] = artifact

    def read_artifact(self, *, job_id: UUID) -> ExamConversionStoredArtifact:
        artifact = self.artifacts.get(job_id)
        if artifact is None:
            raise not_found("ExamConversionArtifact", str(job_id))
        return artifact

    def read_named_artifact(
        self,
        *,
        job_id: UUID,
        artifact_key: str,
    ) -> ExamConversionNamedArtifact:
        for artifact in self.read_artifact(job_id=job_id).named_artifacts:
            if artifact.artifact_key == artifact_key:
                return artifact
        raise not_found("ExamConversionNamedArtifact", artifact_key)

    def delete_artifact(self, *, job_id: UUID) -> None:
        self.artifacts.pop(job_id, None)


def local_public_exam_artifact(
    *,
    source_dxe: PublicExamConverterUpload,
) -> ExamConversionStoredArtifact:
    return ExamConversionStoredArtifact(
        filename="examnet-bundle.zip",
        content_type="application/zip",
        content=b"local bundle",
        source_filename=source_dxe.filename,
        source_content=source_dxe.file_bytes,
        named_artifacts=(
            ExamConversionNamedArtifact(
                artifact_key="examnet_pdf",
                filename="examnet-import.pdf",
                content_type="application/pdf",
                content=b"%PDF fake",
            ),
            ExamConversionNamedArtifact(
                artifact_key="qti_package",
                filename="qti-package.zip",
                content_type="application/zip",
                content=b"qti package",
            ),
            ExamConversionNamedArtifact(
                artifact_key="target_readiness_report",
                filename="target-readiness-report.json",
                content_type="application/json",
                content=(
                    b'{"targets":[{"target":"examnet_pdf","item_id":null,"export_enabled":true}]}'
                ),
            ),
            ExamConversionNamedArtifact(
                artifact_key="ir_json",
                filename="exam-ir.json",
                content_type="application/json",
                content=b"{}",
            ),
            ExamConversionNamedArtifact(
                artifact_key="source_ir_json",
                filename="source-ir.json",
                content_type="application/json",
                content=(
                    b'{"warnings":[{"code":"unsupported_source_fragment",'
                    b'"message":"One source fragment requires review."}]}'
                ),
            ),
        ),
    )
