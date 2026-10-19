"""Unit tests for exam workspace import, reopen, and versioned save handlers."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentResponse,
)
from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
    SaveExamWorkspaceDocumentHandler,
    document_summary,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_saved_index import (
    ListExamWorkspaceDocumentsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKeySuggestion,
    NativeGapAcceptedValues,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserProfile
from skriptoteket.domain.scripting.vault import VaultFile, VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.protocols.identity import ProfileRepositoryProtocol
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    InMemoryEnrichmentJobRepository,
)
from tests.unit.application.curated_apps.handlers.exam_index_test_support import (
    InMemoryExamIndexRepository,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_document_test_support import (
    with_next_revision,
)

_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")
_NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


class FakeUow:
    async def __aenter__(self) -> "FakeUow":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class LineageVaultFileRepository(InMemoryVaultFileRepository):
    """Adds active exam and per-format export uniqueness to the fake."""

    async def create(self, *, file: VaultFile) -> VaultFile:
        if file.document_lineage_id is not None:
            for existing in self.files.values():
                if (
                    existing.user_id == file.user_id
                    and existing.document_lineage_id == file.document_lineage_id
                    and existing.export_format == file.export_format
                    and (file.export_format is not None or existing.deleted_at is None)
                ):
                    raise IntegrityError(
                        "duplicate version", params=None, orig=Exception("duplicate version")
                    )
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
        self.index = InMemoryExamIndexRepository(self.vault_files)
        self.profiles = AsyncMock(spec=ProfileRepositoryProtocol)
        self.profiles.get_by_user_id.return_value = UserProfile(
            user_id=uuid4(), created_at=_NOW, updated_at=_NOW
        )
        self.ids = SequenceIdGenerator([uuid4() for _ in range(10)])
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=self.vault_usage,
            vault_storage=self.vault_storage,
            uow=FakeUow(),
            clock=FixedClock(_NOW),
            settings=_settings(),
            index=self.index,
            codec=self.codec,
        )
        self.get_handler = GetExamWorkspaceDocumentHandler(
            vault_files=self.vault_files,
            codec=self.codec,
            store=self.store,
            jobs=self.enrichment_jobs,
            uow=FakeUow(),
        )
        self.list_handler = ListExamWorkspaceDocumentsHandler(
            index=self.index, profiles=self.profiles, uow=FakeUow()
        )
        self.save_handler = SaveExamWorkspaceDocumentHandler(
            vault_files=self.vault_files,
            codec=self.codec,
            store=self.store,
            id_generator=self.ids,
            jobs=self.enrichment_jobs,
        )

    async def seed_document(
        self, *, actor: User, document: NativeExamDocument | None = None
    ) -> ExamWorkspaceDocumentResponse:
        if document is None:
            document = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes())
        document = document.model_copy(update={"document_id": uuid4()})
        file = await self.store.save(
            actor=actor,
            file_id=self.ids.new_uuid(),
            name="grammatik.provdokument.zip",
            content=self.codec.build(
                content=ExamWorkspaceContainerContent(
                    document=document,
                    assets_by_id={},
                    notes=(),
                )
            ),
            lineage_id=document.document_id,
            version=1,
        )
        return ExamWorkspaceDocumentResponse(
            document=document,
            saved_document=document,
            summary=document_summary(file, document),
            history_cursor=document.document_id,
            conversion=None,
        )


def _steps(env: _Env) -> StoreExamWorkspaceUndoStepHandler:
    """One save-model store over the same persistence ports."""
    return StoreExamWorkspaceUndoStepHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        id_generator=SequenceIdGenerator([uuid4() for _ in range(100)]),
        jobs=env.enrichment_jobs,
    )


async def _store_step(env: _Env, actor: User, lineage: UUID, document: NativeExamDocument) -> None:
    cursor = (await env.save_handler.history(actor=actor, lineage_id=lineage)).cursor
    await _steps(env).handle(
        actor=actor,
        lineage_id=lineage,
        request=StoreExamWorkspaceUndoStepRequest(expected_cursor=cursor, document=document),
    )


@pytest.fixture()
def env() -> _Env:
    return _Env()


@pytest.fixture(scope="module")
def fixture_bytes() -> bytes:
    return _FIXTURE.read_bytes()


@pytest.mark.asyncio
async def test_store_creates_version_one(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    result = await env.seed_document(actor=actor)
    assert result.summary.version == 1
    assert result.summary.name.endswith(".provdokument.zip")
    assert result.document.title == "Omprov: grammatik och språkstrukturer"
    assert result.summary.lineage_id == result.document.document_id
    stored = env.vault_files.files[result.summary.vault_file_id]
    assert stored.document_version == 1
    assert stored.document_lineage_id == result.summary.lineage_id


@pytest.mark.asyncio
async def test_store_uses_authoritative_head_name_not_a_writers_stale_copy(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    original = env.vault_files.files[imported.summary.vault_file_id]
    env.vault_files.files[original.id] = original.model_copy(
        update={"name": "Lärarens namn.provdokument.zip"}
    )
    saved = await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name=original.name,
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(
                document=imported.document.model_copy(update={"revision": 2}),
                assets_by_id={},
                notes=(),
            )
        ),
        lineage_id=imported.summary.lineage_id,
        version=2,
        expected_revision=1,
        preserve_editor_position=True,
    )
    assert saved.name == "Lärarens namn.provdokument.zip"


@pytest.mark.asyncio
async def test_reopen_returns_head_document(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
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
    imported = await env.seed_document(actor=actor)
    await _store_step(
        env, actor, imported.summary.lineage_id, with_next_revision(imported.document)
    )

    listed = await env.list_handler.handle(actor=actor)

    assert [(entry.lineage_id, entry.version) for entry in listed.documents] == [
        (imported.summary.lineage_id, 2)
    ]
    assert (await env.list_handler.handle(actor=_actor())).documents == ()


@pytest.mark.asyncio
async def test_store_advances_version_and_reopens_faithfully(
    env: _Env, fixture_bytes: bytes
) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    document = imported.document
    first_item = document.items[0]
    first_paragraph = first_item.body[0]
    edited_paragraph = first_paragraph.model_copy(
        update={
            "segments": (
                first_paragraph.segments[0].model_copy(update={"text": "Fråga 1 (redigerad)"}),
                *first_paragraph.segments[1:],
            )
        }
    )
    edited_item = first_item.model_copy(update={"body": (edited_paragraph, *first_item.body[1:])})
    edited = document.model_copy(update={"items": (edited_item, *document.items[1:])})

    await _store_step(env, actor, imported.summary.lineage_id, edited)
    reopened = await env.get_handler.handle(actor=actor, lineage_id=imported.summary.lineage_id)
    assert reopened.summary.version == 2
    assert reopened.document.items[0].plain_text_lines()[0] == "Fråga 1 (redigerad)"
    assert reopened.document == edited.model_copy(update={"revision": 2})


@pytest.mark.asyncio
async def test_duplicate_version_insert_maps_to_conflict(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    with pytest.raises(DomainError) as exc_info:
        await env.store.save(
            actor=actor,
            file_id=uuid4(),
            name="x.provdokument.zip",
            content=env.codec.build(
                content=ExamWorkspaceContainerContent(document=imported.document)
            ),
            lineage_id=imported.summary.lineage_id,
            version=1,
        )
    assert exc_info.value.code is ErrorCode.CONFLICT


@pytest.mark.asyncio
async def test_other_user_cannot_reopen_document(env: _Env, fixture_bytes: bytes) -> None:
    owner = _actor()
    imported = await env.seed_document(actor=owner)
    with pytest.raises(DomainError) as exc_info:
        await env.get_handler.handle(actor=_actor(), lineage_id=imported.summary.lineage_id)
    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_store_and_reopen_keep_the_ai_suggestion_on_its_question(
    env: _Env, fixture_bytes: bytes
) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    first = imported.document.items[0]
    suggestion = NativeAnswerKeySuggestion(
        gap_accepted_values=tuple(
            NativeGapAcceptedValues(gap_id=gap.gap_id, accepted_values=("förslag",))
            for gap in first.gaps
        ),
        fingerprint="a" * 64,
        provider_profile_id="profile",
        model="model",
        prompt_template_version="v1",
    )
    saved_document = imported.document.model_copy(
        update={
            "items": (
                first.model_copy(update={"ai_suggestion": suggestion}),
                *imported.document.items[1:],
            ),
        }
    )

    await _store_step(env, actor, imported.summary.lineage_id, saved_document)
    reopened = await env.get_handler.handle(actor=actor, lineage_id=imported.summary.lineage_id)

    kept = reopened.document.items[0].ai_suggestion
    assert kept is not None
    assert kept.model == "model"
    assert [entry.gap_id for entry in kept.gap_accepted_values] == [
        gap.gap_id for gap in first.gaps
    ]
