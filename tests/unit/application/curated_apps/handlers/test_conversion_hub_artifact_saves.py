"""Behavioral tests for authenticated Conversion Hub artifact saves.

This module verifies the Klassrumskartan-style Vault finalization path used by
the authenticated Exam Converter lane for downloaded Sir Convert artifacts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSirConvertArtifactSaveMetadata,
    SaveConversionHubSirConvertArtifactCommand,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_artifact_saves import (
    SaveConversionHubSirConvertArtifactHandler,
)
from skriptoteket.application.curated_apps.sir_convert_contracts import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FixedIdGenerator:
    def __init__(self, value: UUID) -> None:
        self._value = value

    def new_uuid(self) -> UUID:
        return self._value


def _settings(*, max_file_bytes: int = 1_000_000, max_total_bytes: int = 2_000_000) -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=max_file_bytes,
        VAULT_MAX_TOTAL_BYTES=max_total_bytes,
    )


def _metadata(*, content: bytes) -> ConversionHubSirConvertArtifactSaveMetadata:
    return ConversionHubSirConvertArtifactSaveMetadata(
        sir_convert_job_id="sir-job-1",
        artifact_key="examnet_pdf",
        source_filename="examnet-import.pdf",
        saved_display_filename="examnet-import.pdf",
        content_type="application/pdf",
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
        bundle_schema_version=DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
        correlation_id="correlation-1",
        saved_at=datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc),
    )


def _handler(
    *,
    file_id: UUID,
    vault_files: AsyncMock,
    vault_usage: AsyncMock,
    vault_storage: AsyncMock,
    settings: Settings | None = None,
) -> SaveConversionHubSirConvertArtifactHandler:
    return SaveConversionHubSirConvertArtifactHandler(
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 5, 13, 12, 5, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(file_id),
        settings=settings or _settings(),
    )


@pytest.mark.asyncio
async def test_save_sir_convert_artifact_uses_app_export_vault_record() -> None:
    actor = make_user()
    file_id = uuid4()
    content = b"%PDF-1.7\n"
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.create.side_effect = lambda *, file: file
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get_for_update.return_value = VaultUsage(
        user_id=actor.id,
        bytes_total=10,
        updated_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    handler = _handler(
        file_id=file_id,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
    )

    result = await handler.handle(
        actor=actor,
        command=SaveConversionHubSirConvertArtifactCommand(
            metadata=_metadata(content=content),
            filename="examnet-import.pdf",
            content_type="application/pdf",
            content=content,
        ),
    )

    saved_file = vault_files.create.call_args.kwargs["file"]
    assert isinstance(saved_file, VaultFile)
    assert saved_file.user_id == actor.id
    assert saved_file.source_kind is VaultFileSourceKind.APP_EXPORT
    assert saved_file.source_artifact_id == "documents.conversion_hub:sir-job-1:examnet_pdf"
    vault_storage.store_file.assert_awaited_once_with(
        user_id=actor.id,
        file_id=file_id,
        content=content,
    )
    assert result.vault_artifact.file_id == file_id
    assert result.vault_artifact.name == "examnet-import.pdf"
    assert result.vault_artifact.bytes == len(content)


@pytest.mark.asyncio
async def test_save_rejects_checksum_mismatch() -> None:
    actor = make_user()
    content = b"pdf"
    metadata = _metadata(content=content).model_copy(update={"sha256": "0" * 64})
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    handler = _handler(
        file_id=uuid4(),
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
    )

    with pytest.raises(DomainError):
        await handler.handle(
            actor=actor,
            command=SaveConversionHubSirConvertArtifactCommand(
                metadata=metadata,
                filename="examnet-import.pdf",
                content_type="application/pdf",
                content=content,
            ),
        )

    vault_files.create.assert_not_awaited()
    vault_storage.store_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_removes_stored_bytes_when_usage_update_fails() -> None:
    actor = make_user()
    file_id = uuid4()
    content = b"pdf"
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.create.side_effect = lambda *, file: file
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get_for_update.return_value = VaultUsage(
        user_id=actor.id,
        bytes_total=0,
        updated_at=datetime(2026, 5, 13, tzinfo=timezone.utc),
    )
    vault_usage.upsert.side_effect = RuntimeError("db failed")
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    handler = _handler(
        file_id=file_id,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
    )

    with pytest.raises(RuntimeError):
        await handler.handle(
            actor=actor,
            command=SaveConversionHubSirConvertArtifactCommand(
                metadata=_metadata(content=content),
                filename="examnet-import.pdf",
                content_type="application/pdf",
                content=content,
            ),
        )

    vault_storage.delete_file.assert_awaited_once_with(user_id=actor.id, file_id=file_id)
