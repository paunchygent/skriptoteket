"""Typed fake handlers for the Document Converter API facade tests.

Purpose:
    Record the keyword arguments the route functions pass to application
    handlers, so route tests assert on typed call records.

Relationships:
    - Used by `test_apps_document_converter_api`.
"""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
    ConversionHubSubmitResult,
    ConversionHubSubmittedJob,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterJobStatusResult,
    DocumentConverterSubmitResult,
    ListDocumentConverterSavedFilesResult,
    SaveDocumentConverterArtifactResult,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
    JobSpecBuilder,
)
from skriptoteket.domain.identity.models import User


class _CreateJobCall(TypedDict):
    actor: User
    spec: ConversionHubJobSpecV2
    uploads: list[ConversionHubUpload]
    wait_seconds: int
    correlation_id: str | None
    build_job_spec: JobSpecBuilder


class FakeCreateHandler:
    def __init__(self) -> None:
        self.calls: list[_CreateJobCall] = []

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
        self.calls.append(
            {
                "actor": actor,
                "spec": spec,
                "uploads": uploads,
                "wait_seconds": wait_seconds,
                "correlation_id": correlation_id,
                "build_job_spec": build_job_spec,
            }
        )
        return ConversionHubSubmitResult(
            jobs=[
                ConversionHubSubmittedJob(
                    input_filename="source.html",
                    job_id=uuid4(),
                    status=ConversionHubJobStatus.QUEUED,
                    error=None,
                )
            ]
        )


class _JobCall(TypedDict):
    actor: User
    job_id: UUID
    correlation_id: str | None


class FakeGetDocumentConverterHandler:
    def __init__(self, result: DocumentConverterJobStatusResult) -> None:
        self.result = result
        self.calls: list[_JobCall] = []

    async def handle(
        self, *, actor: User, job_id: UUID, correlation_id: str | None
    ) -> DocumentConverterJobStatusResult:
        self.calls.append({"actor": actor, "job_id": job_id, "correlation_id": correlation_id})
        return self.result


class _ArtifactCall(TypedDict):
    actor: User
    job_id: UUID
    correlation_id: str | None
    filename_stem: str | None


class FakeDownloadHandler:
    def __init__(self, *, filename: str = "converted.pdf") -> None:
        self.filename = filename
        self.calls: list[_ArtifactCall] = []

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
        filename_stem: str | None = None,
    ) -> tuple[str, str, bytes]:
        self.calls.append(
            {
                "actor": actor,
                "job_id": job_id,
                "correlation_id": correlation_id,
                "filename_stem": filename_stem,
            }
        )
        return (self.filename, "application/pdf", b"%PDF-1.7")


class FakeSaveHandler:
    def __init__(self, result: SaveDocumentConverterArtifactResult) -> None:
        self.result = result
        self.calls: list[_ArtifactCall] = []

    async def handle(
        self,
        *,
        actor: User,
        job_id: UUID,
        correlation_id: str | None,
        filename_stem: str | None = None,
    ) -> SaveDocumentConverterArtifactResult:
        self.calls.append(
            {
                "actor": actor,
                "job_id": job_id,
                "correlation_id": correlation_id,
                "filename_stem": filename_stem,
            }
        )
        return self.result


class _ActorCall(TypedDict):
    actor: User


class FakeListSavedFilesHandler:
    def __init__(self, result: ListDocumentConverterSavedFilesResult) -> None:
        self.result = result
        self.calls: list[_ActorCall] = []

    async def handle(self, *, actor: User) -> ListDocumentConverterSavedFilesResult:
        self.calls.append({"actor": actor})
        return self.result


class _SavedFileJobCall(TypedDict):
    actor: User
    spec: ConversionHubJobSpecV2
    source_refs: list[str]
    wait_seconds: int
    correlation_id: str | None
    build_job_spec: JobSpecBuilder


class FakeSubmitSavedFileHandler:
    def __init__(self, result: DocumentConverterSubmitResult) -> None:
        self.result = result
        self.calls: list[_SavedFileJobCall] = []

    async def handle(
        self,
        *,
        actor: User,
        spec: ConversionHubJobSpecV2,
        source_refs: list[str],
        wait_seconds: int,
        correlation_id: str | None,
        build_job_spec: JobSpecBuilder,
    ) -> DocumentConverterSubmitResult:
        self.calls.append(
            {
                "actor": actor,
                "spec": spec,
                "source_refs": source_refs,
                "wait_seconds": wait_seconds,
                "correlation_id": correlation_id,
                "build_job_spec": build_job_spec,
            }
        )
        return self.result
