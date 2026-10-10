"""Unit tests for exam workspace import, reopen, and versioned save handlers."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from skriptoteket.application.curated_apps.exam_workspace import (
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
    GetExamWorkspaceDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
    ListExamWorkspaceDocumentsHandler,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_extractor,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)

_FIXTURE = Path(
    "tests/fixtures/exam_conversion/real_inputs/grammatik_omprov_examnet_import_med_facit.docx"
)
_NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


class FakeUow:
    async def __aenter__(self) -> "FakeUow":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class LineageVaultFileRepository(InMemoryVaultFileRepository):
    async def get_document_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> VaultFile | None:
        candidates = [
            file
            for file in self.files.values()
            if file.user_id == user_id
            and file.document_lineage_id == document_lineage_id
            and file.deleted_at is None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda file: file.document_version or 0)

    async def list_document_heads(
        self, *, user_id: UUID, source_artifact_prefix: str
    ) -> list[VaultFile]:
        heads: dict[UUID, VaultFile] = {}
        for file in self.files.values():
            if (
                file.user_id != user_id
                or file.document_lineage_id is None
                or file.deleted_at is not None
                or not (file.source_artifact_id or "").startswith(source_artifact_prefix)
            ):
                continue
            current = heads.get(file.document_lineage_id)
            if current is None or (file.document_version or 0) > (current.document_version or 0):
                heads[file.document_lineage_id] = file
        return sorted(heads.values(), key=lambda file: (file.created_at, file.id), reverse=True)

    async def create(self, *, file: VaultFile) -> VaultFile:
        if file.document_lineage_id is not None:
            for existing in self.files.values():
                if (
                    existing.user_id == file.user_id
                    and existing.document_lineage_id == file.document_lineage_id
                    and existing.document_version == file.document_version
                ):
                    raise IntegrityError("duplicate version", params=None, orig=None)
        return await super().create(file=file)


def _actor() -> User:
    return User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.HULEEDU,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _settings() -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=5_000_000,
        VAULT_MAX_TOTAL_BYTES=50_000_000,
    )


class _Env:
    def __init__(self) -> None:
        self.vault_files = LineageVaultFileRepository()
        self.vault_usage = InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=uuid4(), bytes_total=0, updated_at=_NOW)
        )
        self.vault_storage = InMemoryVaultStorage()
        self.codec = ExamWorkspaceContainerCodec()
        self.ids = SequenceIdGenerator([uuid4() for _ in range(10)])
        self.store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=self.vault_usage,
            vault_storage=self.vault_storage,
            uow=FakeUow(),
            clock=FixedClock(_NOW),
            settings=_settings(),
        )
        self.import_handler = ImportExamWorkspaceDocumentHandler(
            extractor=exam_workspace_docx_extractor.PythonDocxExamExtractor(),
            codec=self.codec,
            store=self.store,
            id_generator=self.ids,
        )
        self.get_handler = GetExamWorkspaceDocumentHandler(
            vault_files=self.vault_files, codec=self.codec, store=self.store
        )
        self.list_handler = ListExamWorkspaceDocumentsHandler(vault_files=self.vault_files)
        self.save_handler = SaveExamWorkspaceDocumentHandler(
            vault_files=self.vault_files,
            codec=self.codec,
            store=self.store,
            id_generator=self.ids,
        )


@pytest.fixture()
def env() -> _Env:
    return _Env()


@pytest.fixture(scope="module")
def fixture_bytes() -> bytes:
    return _FIXTURE.read_bytes()


@pytest.mark.asyncio
async def test_import_creates_version_one(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    result = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    assert result.summary.version == 1
    assert result.summary.name.endswith(".provdokument.zip")
    assert result.document.title == "Omprov: grammatik och språkstrukturer"
    assert result.summary.lineage_id == result.document.document_id
    stored = env.vault_files.files[result.summary.vault_file_id]
    assert stored.document_version == 1
    assert stored.document_lineage_id == result.summary.lineage_id


@pytest.mark.asyncio
async def test_import_rejects_non_docx(env: _Env) -> None:
    with pytest.raises(DomainError) as exc_info:
        await env.import_handler.handle(actor=_actor(), filename="prov.pdf", content=b"x")
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_reopen_returns_head_document(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=imported.summary.lineage_id)
    assert reopened.document == imported.document
    assert reopened.summary.version == 1


@pytest.mark.asyncio
async def test_reopen_unknown_lineage_is_not_found(env: _Env) -> None:
    with pytest.raises(DomainError) as exc_info:
        await env.get_handler.handle(actor=_actor(), lineage_id=uuid4())
    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_list_returns_only_head_version_per_lineage(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=1, document=imported.document.with_revision(2)
        ),
    )

    listed = await env.list_handler.handle(actor=actor)

    assert [(entry.lineage_id, entry.version) for entry in listed.documents] == [
        (imported.summary.lineage_id, 2)
    ]
    assert (await env.list_handler.handle(actor=_actor())).documents == ()


@pytest.mark.asyncio
async def test_save_advances_version_and_reopens_faithfully(
    env: _Env, fixture_bytes: bytes
) -> None:
    actor = _actor()
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    document = imported.document
    edited_item = document.items[0].model_copy(update={"title": "Fråga 1 (redigerad)"})
    edited = document.with_replaced_item(edited_item).with_revision(2)

    saved = await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=edited),
    )
    assert saved.summary.version == 2

    reopened = await env.get_handler.handle(actor=actor, lineage_id=imported.summary.lineage_id)
    assert reopened.summary.version == 2
    assert reopened.document.items[0].title == "Fråga 1 (redigerad)"
    assert reopened.document == edited


@pytest.mark.asyncio
async def test_save_with_stale_revision_conflicts(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    edited = imported.document.with_revision(2)
    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=edited),
    )
    with pytest.raises(DomainError) as exc_info:
        await env.save_handler.handle(
            actor=actor,
            lineage_id=imported.summary.lineage_id,
            request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=edited),
        )
    assert exc_info.value.code is ErrorCode.CONFLICT


@pytest.mark.asyncio
async def test_save_rejects_wrong_document_identity(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    foreign = imported.document.model_copy(update={"document_id": uuid4()}).with_revision(2)
    with pytest.raises(DomainError) as exc_info:
        await env.save_handler.handle(
            actor=actor,
            lineage_id=imported.summary.lineage_id,
            request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=foreign),
        )
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_save_requires_revision_advance_by_one(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    with pytest.raises(DomainError) as exc_info:
        await env.save_handler.handle(
            actor=actor,
            lineage_id=imported.summary.lineage_id,
            request=SaveExamWorkspaceDocumentRequest(
                expected_revision=1, document=imported.document
            ),
        )
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_duplicate_version_insert_maps_to_conflict(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    with pytest.raises(DomainError) as exc_info:
        await env.store.save_version(
            actor=actor,
            file_id=uuid4(),
            name="x.provdokument.zip",
            content=b"payload",
            lineage_id=imported.summary.lineage_id,
            version=1,
        )
    assert exc_info.value.code is ErrorCode.CONFLICT


@pytest.mark.asyncio
async def test_other_user_cannot_reopen_document(env: _Env, fixture_bytes: bytes) -> None:
    owner = _actor()
    imported = await env.import_handler.handle(
        actor=owner, filename=_FIXTURE.name, content=fixture_bytes
    )
    with pytest.raises(DomainError) as exc_info:
        await env.get_handler.handle(actor=_actor(), lineage_id=imported.summary.lineage_id)
    assert exc_info.value.code is ErrorCode.NOT_FOUND
