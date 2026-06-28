"""Behavioral tests for Document Converter artifact content hygiene.

Purpose:
    Prove terminal Document Converter artifacts fail closed when producer bytes
    contain checkpoint, missing-resource, or internal authority markers.

Relationships:
    Exercises the same download and Vault-save application handlers used by the
    scoped Document Converter API before artifacts cross into HTTP or Mina filer.
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
from skriptoteket.application.curated_apps.handlers.conversion_hub_document_converter import (
    DownloadDocumentConverterArtifactHandler,
    SaveDocumentConverterArtifactHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactOutcomeV2,
    SirConvertArtifactV2,
)
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
)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dirty_content",
    [
        b"%PDF-1.7\npdf_checkpointed_output\n",
        b"<!-- sir-convert-a-lot:partial -->",
        b"<img src='project:///__missing_asset__.png'>",
        "Bild saknas".encode("utf-8"),
        "Saknad resurs".encode("utf-8"),
    ],
)
async def test_download_document_converter_artifact_rejects_dirty_terminal_artifact(
    dirty_content: bytes,
) -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(job_id=job_id, owner_user_id=actor.id)
    client = FakeSirConvertClient()
    client.artifacts_by_upstream_id["sir-job-1"] = _artifact(content=dirty_content)
    handler = DownloadDocumentConverterArtifactHandler(
        jobs=repo,
        client=client,
        local_artifacts=InMemoryDocumentConverterArtifactStore(),
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 23, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-dirty")

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_document_converter_artifact_rejects_dirty_terminal_artifact_before_vault() -> (
    None
):
    actor = make_user()
    job_id = uuid4()
    file_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _document_job(job_id=job_id, owner_user_id=actor.id)
    client = FakeSirConvertClient()
    client.artifacts_by_upstream_id["sir-job-1"] = _artifact(
        content=b"%PDF-1.7\npdf_checkpointed_output\n<!-- sir-convert-a-lot:partial -->"
    )
    vault_files = InMemoryVaultFileRepository()
    vault_storage = InMemoryVaultStorage()
    handler = SaveDocumentConverterArtifactHandler(
        jobs=repo,
        client=client,
        local_artifacts=InMemoryDocumentConverterArtifactStore(),
        vault_files=vault_files,
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=actor.id, bytes_total=0, updated_at=datetime.now(timezone.utc))
        ),
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 23, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(file_id),
        settings=_settings(),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-dirty")

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert vault_files.files == {}
    assert vault_storage.stored == {}


def _document_job(
    *,
    job_id: UUID,
    owner_user_id: UUID,
) -> ConversionHubJob:
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    return ConversionHubJob(
        id=job_id,
        owner_user_id=owner_user_id,
        input_filename="source.html",
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.PDF,
        pdf_layout=None,
        upstream_job_id="sir-job-1",
        status=ConversionHubJobStatus.SUCCEEDED,
        correlation_id="corr-1",
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def _artifact(*, content: bytes) -> SirConvertArtifactOutcomeV2:
    return SirConvertArtifactOutcomeV2(
        job_id="sir-job-1",
        status="succeeded",
        artifact=SirConvertArtifactV2(
            filename="source.pdf",
            content_type="application/pdf",
            content=content,
        ),
    )


def _settings() -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=1_000_000,
        VAULT_MAX_TOTAL_BYTES=2_000_000,
    )
