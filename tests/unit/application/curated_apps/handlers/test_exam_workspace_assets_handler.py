"""The head-revision picture reader: declared payload, media type and not-found paths (D2)."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_assets import (
    GetExamWorkspaceAssetHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import asset_id_for
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.vault import VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    choice,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)

_NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


class _Uow:
    async def __aenter__(self) -> "_Uow":
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


def _document_with_asset() -> tuple[NativeExamDocument, bytes, str]:
    payload = b"picture-bytes"
    asset_id = asset_id_for(payload)
    item = choice("body:0001", "Fråga ett").model_copy(
        update={
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Fråga ett", marks=()),
                        NativeAssetSegment(asset_id=asset_id),
                    ),
                ),
            )
        }
    )
    asset = NativeExamAsset(
        asset_id=asset_id,
        sha256=sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=(item,),
        assets=(asset,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return document, payload, asset_id


class _Env:
    def __init__(self) -> None:
        self.vault_files = InMemoryVaultFileRepository()
        self.codec = ExamWorkspaceContainerCodec()
        self.store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=InMemoryVaultUsageRepository(
                usage=VaultUsage(user_id=uuid4(), bytes_total=0, updated_at=_NOW)
            ),
            vault_storage=InMemoryVaultStorage(),
            uow=_Uow(),
            clock=FixedClock(_NOW),
            settings=Settings.model_construct(
                VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
            ),
        )
        self.handler = GetExamWorkspaceAssetHandler(
            vault_files=self.vault_files, codec=self.codec, store=self.store
        )

    async def seed(self, actor: User) -> tuple[NativeExamDocument, bytes, str]:
        document, payload, asset_id = _document_with_asset()
        await self.store.save(
            actor=actor,
            file_id=uuid4(),
            name="prov.provdokument.zip",
            content=self.codec.build(
                content=ExamWorkspaceContainerContent(
                    document=document,
                    assets_by_id={asset_id: payload},
                    notes=(),
                )
            ),
            lineage_id=document.document_id,
            version=1,
        )
        return document, payload, asset_id


@pytest.mark.asyncio
async def test_a_declared_picture_is_served_with_its_media_type() -> None:
    env = _Env()
    actor = _actor()
    document, payload, asset_id = await env.seed(actor)

    asset = await env.handler.handle(
        actor=actor, lineage_id=document.document_id, asset_id=asset_id
    )

    assert asset.content == payload
    assert asset.media_type == "image/png"


@pytest.mark.asyncio
async def test_an_unknown_asset_id_is_not_found() -> None:
    env = _Env()
    actor = _actor()
    document, _, _ = await env.seed(actor)

    with pytest.raises(DomainError) as exc_info:
        await env.handler.handle(
            actor=actor, lineage_id=document.document_id, asset_id=asset_id_for(b"other")
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_another_actors_document_is_not_found() -> None:
    env = _Env()
    actor = _actor()
    document, _, asset_id = await env.seed(actor)

    with pytest.raises(DomainError) as exc_info:
        await env.handler.handle(actor=_actor(), lineage_id=document.document_id, asset_id=asset_id)

    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_a_missing_document_is_not_found() -> None:
    env = _Env()

    with pytest.raises(DomainError) as exc_info:
        await env.handler.handle(
            actor=_actor(), lineage_id=uuid4(), asset_id=asset_id_for(b"other")
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
