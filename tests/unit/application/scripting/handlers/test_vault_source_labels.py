"""Mina filer source labels for APP_EXPORT files.

The label is the canonical curated registry title for the app id before the
first ``:`` in ``source_artifact_id``. Unregistered or empty prefixes get
"App-export".
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.handlers.list_vault_files import ListVaultFilesHandler
from skriptoteket.application.scripting.vault import ListVaultFilesQuery
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListState,
    VaultUsage,
)
from skriptoteket.infrastructure.curated_apps.registry import InMemoryCuratedAppRegistry
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

_NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


class FakeUow:
    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


def _actor() -> User:
    return User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.HULEEDU,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _app_export(*, user_id: UUID, source_artifact_id: str | None) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name="export.zip",
        bytes=10,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id=source_artifact_id,
        created_at=_NOW,
        deleted_at=None,
    )


async def _label_for(source_artifact_id: str | None) -> str | None:
    actor = _actor()
    vault_file = _app_export(user_id=actor.id, source_artifact_id=source_artifact_id)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.list_for_user.return_value = [vault_file]
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get.return_value = VaultUsage(user_id=actor.id, bytes_total=10, updated_at=_NOW)
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    vault_storage.exists_file.return_value = True
    settings = Settings(VAULT_MAX_TOTAL_BYTES=1000, VAULT_MAX_FILE_BYTES=1000)

    handler = ListVaultFilesHandler(
        uow=FakeUow(),
        runs=AsyncMock(spec=ToolRunRepositoryProtocol),
        tools=AsyncMock(spec=ToolRepositoryProtocol),
        curated_apps=InMemoryCuratedAppRegistry(settings=settings),
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        settings=settings,
    )
    result = await handler.handle(
        actor=actor, query=ListVaultFilesQuery(state=VaultListState.ACTIVE)
    )
    [info] = result.files
    return info.source_label


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_artifact_id", "expected_title"),
    [
        pytest.param("chemistry.reagent_prep_chef", "Reagensberedning", id="reagent-plain-id"),
        pytest.param("classroom.group-seating-studio", "Klassrumskartan", id="seating-plain-id"),
        pytest.param(
            f"documents.conversion_hub:exam-converter:{uuid4()}:qti_package",
            "Provhantering",
            id="exam-converter-artifact",
        ),
        pytest.param(
            f"documents.conversion_hub:exam-workspace:{uuid4()}:v3",
            "Provhantering",
            id="exam-workspace-version",
        ),
        pytest.param(
            f"documents.conversion_hub:transcript-export:{uuid4()}:transcript_txt",
            "Provhantering",
            id="transcript-export",
        ),
        pytest.param(
            f" documents.conversion_hub :exam-workspace:{uuid4()}:v1",
            "Provhantering",
            id="padded-prefix",
        ),
    ],
)
async def test_app_export_label_is_registry_title_for_app_id_prefix(
    source_artifact_id: str, expected_title: str
) -> None:
    assert await _label_for(source_artifact_id) == expected_title


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_artifact_id",
    [
        pytest.param("unknown.app:exam-workspace:abc:v1", id="unknown-prefix"),
        pytest.param(f"document-converter:{uuid4()}:docx", id="unregistered-document-converter"),
        pytest.param("", id="empty"),
        pytest.param(None, id="absent"),
        pytest.param(":exam-workspace:abc:v1", id="empty-prefix"),
    ],
)
async def test_app_export_label_falls_back_for_unregistered_or_empty_prefix(
    source_artifact_id: str | None,
) -> None:
    assert await _label_for(source_artifact_id) == "App-export"
