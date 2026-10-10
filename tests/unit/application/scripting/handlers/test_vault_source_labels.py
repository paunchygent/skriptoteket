"""Mina filer source labels for APP_EXPORT files.

Apps save exports with either a plain curated app id or an app-scoped
artifact id shaped ``<app_id>:<app-specific parts>``. The list handler must
resolve the app title from the prefix before the first ``:`` for every shape.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.handlers._vault_helpers import (
    app_id_from_source_artifact_id,
)
from skriptoteket.application.scripting.handlers.list_vault_files import ListVaultFilesHandler
from skriptoteket.application.scripting.vault import ListVaultFilesQuery
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListState,
    VaultUsage,
)
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)

_NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
_APP_ID = "documents.conversion_hub"
_APP_TITLE = "Konverteringshubben"


class FakeUow:
    async def __aenter__(self) -> FakeUow:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeCuratedApps:
    def __init__(self) -> None:
        self._app = CuratedAppDefinition(
            app_id=_APP_ID,
            tool_id=curated_app_tool_id(app_id=_APP_ID),
            app_version="1",
            title=_APP_TITLE,
            placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
        )

    def list_all(self) -> list[CuratedAppDefinition]:
        return [self._app]

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return self._app if app_id == _APP_ID else None

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
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


def _app_export(*, user_id: UUID, source_artifact_id: str) -> VaultFile:
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


async def _label_for(source_artifact_id: str) -> str | None:
    actor = _actor()
    vault_file = _app_export(user_id=actor.id, source_artifact_id=source_artifact_id)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.list_for_user.return_value = [vault_file]
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get.return_value = VaultUsage(user_id=actor.id, bytes_total=10, updated_at=_NOW)
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    vault_storage.exists_file.return_value = True

    handler = ListVaultFilesHandler(
        uow=FakeUow(),
        runs=AsyncMock(spec=ToolRunRepositoryProtocol),
        tools=AsyncMock(spec=ToolRepositoryProtocol),
        curated_apps=FakeCuratedApps(),
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        settings=Settings.model_construct(VAULT_MAX_TOTAL_BYTES=1000, VAULT_MAX_FILE_BYTES=1000),
    )
    result = await handler.handle(
        actor=actor, query=ListVaultFilesQuery(state=VaultListState.ACTIVE)
    )
    [info] = result.files
    return info.source_label


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_artifact_id",
    [
        pytest.param(_APP_ID, id="plain-app-id"),
        pytest.param(
            f"{_APP_ID}:exam-converter:{uuid4()}:examnet_qti_package",
            id="exam-converter-artifact",
        ),
        pytest.param(f"{_APP_ID}:exam-workspace:{uuid4()}:v3", id="exam-workspace-version"),
    ],
)
async def test_app_export_label_resolves_app_title_for_every_source_shape(
    source_artifact_id: str,
) -> None:
    assert await _label_for(source_artifact_id) == _APP_TITLE


@pytest.mark.asyncio
async def test_unknown_app_prefix_falls_back_to_generic_label() -> None:
    assert await _label_for("unknown.app:exam-workspace:abc:v1") == "App-export"


@pytest.mark.parametrize(
    ("source_artifact_id", "expected"),
    [
        (None, ""),
        ("", ""),
        (" documents.conversion_hub ", _APP_ID),
        ("documents.conversion_hub:exam-workspace:abc:v2", _APP_ID),
    ],
)
def test_app_id_from_source_artifact_id(source_artifact_id: str | None, expected: str) -> None:
    assert app_id_from_source_artifact_id(source_artifact_id) == expected
