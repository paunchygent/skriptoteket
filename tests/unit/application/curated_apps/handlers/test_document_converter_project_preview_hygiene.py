"""Behavioral tests for Document Converter project preview artifact hygiene.

Purpose:
    Prove stored HTML/CSS project preview artifacts fail closed if stale or
    malformed bytes contain generated missing-resource or internal id markers.

Relationships:
    Exercises project-preview download and save handlers before temporary PDFs
    cross into HTTP responses or Mina filer persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.handlers.document_converter_project_previews import (
    DownloadDocumentConverterProjectPreviewArtifactHandler,
    SaveDocumentConverterProjectPreviewArtifactHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultUsage
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.time_fixtures import (
    FixedClock,
    FixedIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_project_previews import (
    InMemoryProjectPreviewStore,
    _store_preview,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_project_preview_artifact_rejects_dirty_stored_preview() -> None:
    actor = make_user()
    preview_id = uuid4()
    artifact_id = uuid4()
    store = InMemoryProjectPreviewStore()
    await _store_preview(actor=actor, preview_id=preview_id, artifact_id=artifact_id, store=store)
    store.artifacts[(actor.id, preview_id, artifact_id)] = DocumentConverterStoredArtifact(
        filename="preview.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.7\nproject:///__missing_asset__.png\n",
    )
    handler = DownloadDocumentConverterProjectPreviewArtifactHandler(
        previews=store,
        clock=FixedClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, preview_id=preview_id, artifact_id=artifact_id)

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_project_preview_artifact_rejects_internal_ids_before_vault() -> None:
    actor = make_user()
    preview_id = uuid4()
    artifact_id = uuid4()
    file_id = uuid4()
    store = InMemoryProjectPreviewStore()
    await _store_preview(actor=actor, preview_id=preview_id, artifact_id=artifact_id, store=store)
    store.artifacts[(actor.id, preview_id, artifact_id)] = DocumentConverterStoredArtifact(
        filename="preview.pdf",
        content_type="application/pdf",
        content=f"%PDF-1.7\n{preview_id}\n".encode("utf-8"),
    )
    vault_files = InMemoryVaultFileRepository()
    vault_storage = InMemoryVaultStorage()
    handler = SaveDocumentConverterProjectPreviewArtifactHandler(
        previews=store,
        vault_files=vault_files,
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=actor.id, bytes_total=0, updated_at=datetime.now(timezone.utc))
        ),
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(file_id),
        settings=Settings.model_construct(
            VAULT_MAX_FILE_BYTES=1_000_000,
            VAULT_MAX_TOTAL_BYTES=2_000_000,
        ),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, preview_id=preview_id, artifact_id=artifact_id)

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert vault_files.files == {}
    assert vault_storage.stored == {}
