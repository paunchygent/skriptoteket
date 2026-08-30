"""Behavioral tests for Document Converter artifact ownership and saves.

Purpose:
    Prove the Document Converter MVP saves the single converted artifact through
    server-side producer authority and local owner-scoped job ids.

Relationships:
    Exercises the document-converter handlers that sit between the Conversion
    Hub local job ledger, Sir Convert v2, and Vault ``APP_EXPORT`` persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_document_converter import (
    DownloadDocumentConverterArtifactHandler,
    GetDocumentConverterJobHandler,
    SaveDocumentConverterArtifactHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListSort,
    VaultListState,
    VaultUsage,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactOutcomeV2,
    SirConvertArtifactV2,
    SirConvertJobStatusV2,
    SirConvertJobV2,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.time_fixtures import (
    FixedClock,
    FixedIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    FakeSirConvertClient,
    InMemoryConversionHubJobRepository,
    SequenceClock,
)


class InMemoryVaultFileRepository:
    def __init__(self) -> None:
        self.files: dict[UUID, VaultFile] = {}

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        return self.files.get(file_id)

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        state: VaultListState,
        search: str | None,
        sort: VaultListSort,
        limit: int,
        offset: int,
    ) -> list[VaultFile]:
        del state, search, sort, limit, offset
        return [file for file in self.files.values() if file.user_id == user_id]

    async def list_active_for_user(self, *, user_id: UUID) -> list[VaultFile]:
        return [
            file
            for file in self.files.values()
            if file.user_id == user_id and file.deleted_at is None
        ]

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        include_deleted: bool,
    ) -> list[VaultFile]:
        files = [self.files[file_id] for file_id in file_ids if file_id in self.files]
        if include_deleted:
            return [file for file in files if file.user_id == user_id]
        return [file for file in files if file.user_id == user_id and file.deleted_at is None]

    async def list_expired(self, *, cutoff: datetime, limit: int) -> list[VaultFile]:
        del cutoff, limit
        return []

    async def create(self, *, file: VaultFile) -> VaultFile:
        self.files[file.id] = file
        return file

    async def update(self, *, file: VaultFile) -> VaultFile:
        self.files[file.id] = file
        return file

    async def delete(self, *, file_id: UUID) -> None:
        self.files.pop(file_id, None)


class InMemoryVaultUsageRepository:
    def __init__(self, *, usage: VaultUsage) -> None:
        self.usage = usage
        self.fail_upsert = False

    async def get(self, *, user_id: UUID) -> VaultUsage | None:
        if self.usage.user_id != user_id:
            return None
        return self.usage

    async def get_for_update(self, *, user_id: UUID, now: datetime) -> VaultUsage:
        if self.usage.user_id != user_id:
            return VaultUsage(user_id=user_id, bytes_total=0, updated_at=now)
        return self.usage

    async def upsert(self, *, usage: VaultUsage) -> VaultUsage:
        if self.fail_upsert:
            raise RuntimeError("usage failed")
        self.usage = usage
        return usage

    async def recompute_total(self, *, user_id: UUID, now: datetime) -> int:
        del now
        if self.usage.user_id != user_id:
            return 0
        return self.usage.bytes_total


class InMemoryVaultStorage:
    def __init__(self) -> None:
        self.stored: dict[tuple[UUID, UUID], bytes] = {}
        self.deleted: list[tuple[UUID, UUID]] = []
        self.fail_store = False

    async def store_file(self, *, user_id: UUID, file_id: UUID, content: bytes) -> None:
        if self.fail_store:
            raise RuntimeError("store failed")
        self.stored[(user_id, file_id)] = content

    async def exists_file(self, *, user_id: UUID, file_id: UUID) -> bool:
        return (user_id, file_id) in self.stored

    async def read_file(self, *, user_id: UUID, file_id: UUID) -> bytes:
        return self.stored[(user_id, file_id)]

    async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
        self.deleted.append((user_id, file_id))


class InMemoryDocumentConverterArtifactStore:
    def __init__(self) -> None:
        self.artifacts: dict[UUID, DocumentConverterStoredArtifact] = {}

    def store_artifact(
        self,
        *,
        job_id: UUID,
        artifact: DocumentConverterStoredArtifact,
    ) -> None:
        self.artifacts[job_id] = artifact

    def read_artifact(self, *, job_id: UUID) -> DocumentConverterStoredArtifact:
        return self.artifacts[job_id]


def _settings(*, max_file_bytes: int = 1_000_000, max_total_bytes: int = 2_000_000) -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=max_file_bytes,
        VAULT_MAX_TOTAL_BYTES=max_total_bytes,
    )


def _document_job(
    *,
    job_id: UUID,
    owner_user_id: UUID,
    status: ConversionHubJobStatus = ConversionHubJobStatus.SUCCEEDED,
    upstream_job_id: str | None = "sir-job-1",
) -> ConversionHubJob:
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    return ConversionHubJob(
        id=job_id,
        owner_user_id=owner_user_id,
        input_filename="source.html",
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.PDF,
        pdf_layout=None,
        upstream_job_id=upstream_job_id,
        status=status,
        correlation_id="corr-1",
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def _exam_job(*, job_id: UUID, owner_user_id: UUID) -> ConversionHubJob:
    return _document_job(
        job_id=job_id,
        owner_user_id=owner_user_id,
    ).model_copy(
        update={
            "input_filename": "exam.dxe",
            "source_format": ConversionHubSourceFormatV2.DIGIEXAM_DXE,
            "output_format": ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        }
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_document_converter_job_preserves_disabled_route_history() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(
        job_id=job_id,
        owner_user_id=actor.id,
    ).model_copy(
        update={
            "input_filename": "mall.docx",
            "source_format": ConversionHubSourceFormatV2.DOCX,
            "output_format": ConversionHubOutputFormatV2.PDF,
        }
    )
    handler = GetDocumentConverterJobHandler(
        jobs=repo,
        client=FakeSirConvertClient(),
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
    )

    result = await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    assert result.job_id == job_id
    assert result.status is ConversionHubJobStatus.SUCCEEDED


def _artifact(*, content: bytes = b"%PDF-1.7") -> SirConvertArtifactOutcomeV2:
    return SirConvertArtifactOutcomeV2(
        job_id="sir-job-1",
        status="succeeded",
        artifact=SirConvertArtifactV2(
            filename="source.pdf",
            content_type="application/pdf",
            content=content,
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_document_converter_job_adds_result_artifact_after_success() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(job_id=job_id, owner_user_id=actor.id)
    handler = GetDocumentConverterJobHandler(
        jobs=repo,
        client=FakeSirConvertClient(),
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 23, tzinfo=timezone.utc)),
    )

    result = await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert result.result_artifact is not None
    assert result.result_artifact.source_artifact_id == (
        "document-converter:sir-job-1:converted_document"
    )
    assert result.result_artifact.filename == "source - Konverterad PDF - 20260623.pdf"
    assert result.result_artifact.content_type == "application/pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_document_converter_job_keeps_running_upstream_job_in_progress() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(
        job_id=job_id,
        owner_user_id=actor.id,
        status=ConversionHubJobStatus.QUEUED,
    )
    client = FakeSirConvertClient()
    client.jobs_by_upstream_id["sir-job-1"] = SirConvertJobV2(
        job_id="sir-job-1",
        status=SirConvertJobStatusV2.RUNNING,
    )
    handler = GetDocumentConverterJobHandler(
        jobs=repo,
        client=client,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 23, 0, 0, 1, tzinfo=timezone.utc)),
    )

    result = await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-running")

    assert result.status is ConversionHubJobStatus.PROCESSING
    assert result.error is None
    assert result.result_artifact is None
    assert repo.jobs[job_id].status is ConversionHubJobStatus.PROCESSING


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_document_converter_job_hides_non_document_job() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _exam_job(job_id=job_id, owner_user_id=actor.id)
    handler = GetDocumentConverterJobHandler(
        jobs=repo,
        client=FakeSirConvertClient(),
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 23, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    assert excinfo.value.code is ErrorCode.NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_document_converter_artifact_rejects_pending_job() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(
        job_id=job_id,
        owner_user_id=actor.id,
        status=ConversionHubJobStatus.PROCESSING,
    )
    client = FakeSirConvertClient()
    client.jobs_by_upstream_id["sir-job-1"] = SirConvertJobV2(
        job_id="sir-job-1",
        status=SirConvertJobStatusV2.RUNNING,
    )
    handler = DownloadDocumentConverterArtifactHandler(
        jobs=repo,
        client=client,
        local_artifacts=InMemoryDocumentConverterArtifactStore(),
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 23, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_document_converter_artifact_downloads_and_stores_default_result() -> None:
    actor = make_user()
    job_id = uuid4()
    file_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(job_id=job_id, owner_user_id=actor.id)
    client = FakeSirConvertClient()
    client.artifacts_by_upstream_id["sir-job-1"] = _artifact(content=b"%PDF-1.7\n")
    vault_files = InMemoryVaultFileRepository()
    vault_usage = InMemoryVaultUsageRepository(
        usage=VaultUsage(
            user_id=actor.id,
            bytes_total=10,
            updated_at=datetime(2026, 6, 23, tzinfo=timezone.utc),
        )
    )
    vault_storage = InMemoryVaultStorage()
    handler = SaveDocumentConverterArtifactHandler(
        jobs=repo,
        client=client,
        local_artifacts=InMemoryDocumentConverterArtifactStore(),
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 23, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(file_id),
        settings=_settings(),
    )

    result = await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    saved_file = vault_files.files[file_id]
    assert saved_file.user_id == actor.id
    assert saved_file.name == "source - Konverterad PDF - 20260623.pdf"
    assert saved_file.bytes == len(b"%PDF-1.7\n")
    assert saved_file.source_kind is VaultFileSourceKind.APP_EXPORT
    assert saved_file.source_artifact_id == "document-converter:sir-job-1:converted_document"
    assert vault_storage.stored[(actor.id, file_id)] == b"%PDF-1.7\n"
    assert result.vault_artifact.file_id == file_id
    assert result.source_artifact_id == "document-converter:sir-job-1:converted_document"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_document_converter_artifact_hides_foreign_job() -> None:
    actor = make_user()
    other = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(job_id=job_id, owner_user_id=other.id)
    handler = SaveDocumentConverterArtifactHandler(
        jobs=repo,
        client=FakeSirConvertClient(),
        local_artifacts=InMemoryDocumentConverterArtifactStore(),
        vault_files=InMemoryVaultFileRepository(),
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=actor.id, bytes_total=0, updated_at=datetime.now(timezone.utc))
        ),
        vault_storage=InMemoryVaultStorage(),
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 23, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(uuid4()),
        settings=_settings(),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    assert excinfo.value.code is ErrorCode.NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_document_converter_artifact_rolls_back_stored_bytes_on_usage_failure() -> None:
    actor = make_user()
    job_id = uuid4()
    file_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(job_id=job_id, owner_user_id=actor.id)
    client = FakeSirConvertClient()
    client.artifacts_by_upstream_id["sir-job-1"] = _artifact(content=b"%PDF-1.7\n")
    vault_files = InMemoryVaultFileRepository()
    vault_usage = InMemoryVaultUsageRepository(
        usage=VaultUsage(user_id=actor.id, bytes_total=0, updated_at=datetime.now(timezone.utc))
    )
    vault_usage.fail_upsert = True
    vault_storage = InMemoryVaultStorage()
    handler = SaveDocumentConverterArtifactHandler(
        jobs=repo,
        client=client,
        local_artifacts=InMemoryDocumentConverterArtifactStore(),
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 23, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(file_id),
        settings=_settings(),
    )

    with pytest.raises(RuntimeError):
        await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    assert vault_storage.deleted == [(actor.id, file_id)]
