"""Unit tests for exam workspace import, reopen, and versioned save handlers."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentResponse,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
    SaveExamWorkspaceDocumentHandler,
    _summary,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_saved_index import (
    ListExamWorkspaceDocumentsHandler,
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
    InMemoryProposedOverlayRepository,
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
        self.proposed_overlays = InMemoryProposedOverlayRepository()
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

    async def seed_document(self, *, actor: User) -> ExamWorkspaceDocumentResponse:
        document = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes()).model_copy(
            update={"document_id": uuid4()}
        )
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
            summary=_summary(file, document),
            history_cursor=document.document_id,
            conversion=None,
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
    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=1, document=with_next_revision(imported.document)
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
    edited = with_next_revision(
        document.model_copy(update={"items": (edited_item, *document.items[1:])})
    )

    saved = await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=edited),
    )
    assert saved.summary.version == 2

    reopened = await env.get_handler.handle(actor=actor, lineage_id=imported.summary.lineage_id)
    assert reopened.summary.version == 2
    assert reopened.document.items[0].plain_text_lines()[0] == "Fråga 1 (redigerad)"
    assert reopened.document == edited


@pytest.mark.asyncio
async def test_save_with_stale_revision_conflicts(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    edited = with_next_revision(imported.document)
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
    imported = await env.seed_document(actor=actor)
    foreign = with_next_revision(imported.document.model_copy(update={"document_id": uuid4()}))
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
    imported = await env.seed_document(actor=actor)
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


def test_save_request_refuses_the_deleted_rejected_proposal_ids_field() -> None:
    document = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes())
    with pytest.raises(ValidationError):
        SaveExamWorkspaceDocumentRequest.model_validate(
            {
                "expected_revision": 1,
                "document": document.model_dump(mode="json"),
                "rejected_proposal_item_ids": ["item_001"],
            }
        )


def _save_payload_with_key(
    item_id: str, key: dict[str, object], gap_values: list[str]
) -> dict[str, object]:
    payload = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes()).model_dump(mode="json")
    payload["revision"] = 2
    item = next(entry for entry in payload["items"] if entry["item_id"] == item_id)
    item["answer_key"] = {"correct_choice_ids": [], "match_pairs": [], **key}
    for gap in item["gaps"]:
        gap["accepted_values"] = gap_values
    return {"expected_revision": 1, "document": payload}


def test_save_request_accepts_a_machine_proposed_key_that_fits_its_question() -> None:
    request = SaveExamWorkspaceDocumentRequest.model_validate(
        _save_payload_with_key("item_001", {"origin": "machine_proposed"}, ["förslag"])
    )

    assert request.document.items[0].answer_key.origin.value == "machine_proposed"


@pytest.mark.parametrize(
    ("label", "item_id", "key", "gap_values"),
    [
        (
            "choice ids on a gap question",
            "item_001",
            {"origin": "machine_proposed", "correct_choice_ids": ["choice_001"]},
            ["förslag"],
        ),
        (
            "match pairs on a gap question",
            "item_001",
            {
                "origin": "machine_proposed",
                "match_pairs": [{"left_id": "left_001", "right_id": "right_001"}],
            },
            ["förslag"],
        ),
        ("gap key with gaps left unkeyed", "item_001", {"origin": "machine_proposed"}, []),
        (
            "choice key on a free_text question",
            "item_008",
            {"origin": "machine_proposed", "correct_choice_ids": ["choice_001"]},
            [],
        ),
    ],
)
def test_save_request_refuses_a_key_that_does_not_fit_its_question(
    label: str, item_id: str, key: dict[str, object], gap_values: list[str]
) -> None:
    with pytest.raises(ValidationError):
        SaveExamWorkspaceDocumentRequest.model_validate(
            _save_payload_with_key(item_id, key, gap_values)
        )


@pytest.mark.asyncio
async def test_save_and_reopen_keep_the_ai_suggestion_on_its_question(
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
            "revision": 2,
            "items": (
                first.model_copy(update={"ai_suggestion": suggestion}),
                *imported.document.items[1:],
            ),
        }
    )

    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=saved_document),
    )
    reopened = await env.get_handler.handle(actor=actor, lineage_id=imported.summary.lineage_id)

    kept = reopened.document.items[0].ai_suggestion
    assert kept is not None
    assert kept.model == "model"
    assert [entry.gap_id for entry in kept.gap_accepted_values] == [
        gap.gap_id for gap in first.gaps
    ]
