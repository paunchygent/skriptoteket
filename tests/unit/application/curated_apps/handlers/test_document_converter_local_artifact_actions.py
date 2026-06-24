"""Document Converter local artifact action tests.

Purpose:
    Prove locally produced Document Converter artifacts are downloaded and
    saved through the owner-scoped local job id rather than browser-supplied
    artifact keys.

Relationships:
    Complements ``test_document_converter_artifact_saves`` by covering the
    local producer branch introduced in PR-0381.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJobStatus
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
    build_local_document_converter_producer_id,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_document_converter import (
    DownloadDocumentConverterArtifactHandler,
    SaveDocumentConverterArtifactHandler,
)
from skriptoteket.domain.scripting.vault import VaultFileSourceKind, VaultUsage
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.test_conversion_hub_artifact_saves import (
    FixedClock,
    FixedIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    FakeSirConvertClient,
    InMemoryConversionHubJobRepository,
    SequenceClock,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryDocumentConverterArtifactStore,
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
    _document_job,
    _settings,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_document_converter_artifact_reads_local_store_for_local_job() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(
        job_id=job_id,
        owner_user_id=actor.id,
        upstream_job_id=build_local_document_converter_producer_id(job_id=job_id),
    )
    store = InMemoryDocumentConverterArtifactStore()
    store.artifacts[job_id] = DocumentConverterStoredArtifact(
        filename="source.pdf",
        content_type="application/pdf",
        content=b"%PDF-LOCAL",
    )
    client = FakeSirConvertClient()
    handler = DownloadDocumentConverterArtifactHandler(
        jobs=repo,
        client=client,
        local_artifacts=store,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
    )

    filename, content_type, content = await handler.handle(
        actor=actor,
        job_id=job_id,
        correlation_id="corr-1",
    )

    assert filename == "source.pdf"
    assert content_type == "application/pdf"
    assert content == b"%PDF-LOCAL"
    assert client.artifacts_by_upstream_id == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_document_converter_artifact_stores_local_result_in_vault() -> None:
    actor = make_user()
    job_id = uuid4()
    file_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(
        job_id=job_id,
        owner_user_id=actor.id,
        status=ConversionHubJobStatus.SUCCEEDED,
        upstream_job_id=build_local_document_converter_producer_id(job_id=job_id),
    )
    store = InMemoryDocumentConverterArtifactStore()
    store.artifacts[job_id] = DocumentConverterStoredArtifact(
        filename="source.pdf",
        content_type="application/pdf",
        content=b"%PDF-LOCAL",
    )
    vault_files = InMemoryVaultFileRepository()
    vault_storage = InMemoryVaultStorage()
    handler = SaveDocumentConverterArtifactHandler(
        jobs=repo,
        client=FakeSirConvertClient(),
        local_artifacts=store,
        vault_files=vault_files,
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(
                user_id=actor.id,
                bytes_total=0,
                updated_at=datetime(2026, 6, 25, tzinfo=timezone.utc),
            )
        ),
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(file_id),
        settings=_settings(),
    )

    result = await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    saved_file = vault_files.files[file_id]
    assert saved_file.source_kind is VaultFileSourceKind.APP_EXPORT
    assert saved_file.source_artifact_id == f"document-converter:local:{job_id}:converted_document"
    assert vault_storage.stored[(actor.id, file_id)] == b"%PDF-LOCAL"
    assert result.vault_artifact.file_id == file_id
