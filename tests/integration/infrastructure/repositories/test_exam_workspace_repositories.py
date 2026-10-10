"""PostgreSQL coverage for exam workspace persistence seams (TASK-SKRIPT-39-04-01).

Covers the versioned Mina filer document lineage (head lookup, head listing,
and the duplicate-version CONFLICT path through the real unique index) and
workspace-kind answer-key enrichment jobs (revision lookup and the partial
unique index that leaves DXE jobs unconstrained).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    enqueue_enrichment_job,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_workspace import SaveExamWorkspaceDocumentRequest
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX,
    ExamWorkspaceDocumentStore,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    GetExamWorkspaceEnrichmentStatusHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_proposal_carry_forward import (
    CarryExamWorkspaceProposals,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.conversion_hub_jobs import (
    PostgreSQLConversionHubJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_proposed_overlays import (
    PostgreSQLExamAnswerKeyProposedOverlayRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.exam_workspace_proposals import (
    proposal_document,
    proposal_ledger,
    saved_proposal_document,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_exam_answer_key_enrichment_jobs import (
    UUIDGenerator,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

_WORKSPACE_PREFIX = f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:"


async def _create_owner(session_factory: async_sessionmaker[AsyncSession]) -> User:
    owner_id = uuid4()
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        session.add(
            UserModel(
                id=owner_id,
                email=f"exam-workspace-{owner_id}@example.test",
                password_hash="hash",
                role=Role.USER,
                auth_provider=AuthProvider.LOCAL,
                created_at=now,
                updated_at=now,
            )
        )
    return User(
        id=owner_id,
        email=f"exam-workspace-{owner_id}@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


def _version_file(
    *,
    owner_id: UUID,
    lineage_id: UUID,
    version: int,
    created_at: datetime,
    source_artifact_id: str | None = None,
) -> VaultFile:
    return VaultFile(
        id=uuid4(),
        user_id=owner_id,
        name="prov.provdokument.zip",
        bytes=10,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id=source_artifact_id
        or f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:{lineage_id}:v{version}",
        document_lineage_id=lineage_id,
        document_version=version,
        created_at=created_at,
        deleted_at=None,
    )


async def _insert_files(
    session_factory: async_sessionmaker[AsyncSession], files: list[VaultFile]
) -> None:
    async with session_factory() as session, session.begin():
        repository = PostgreSQLUserVaultFileRepository(session)
        for file in files:
            await repository.create(file=file)


async def test_get_document_head_returns_newest_active_version_for_its_owner(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await _create_owner(session_factory)
    stranger = await _create_owner(session_factory)
    lineage_id = uuid4()
    base = datetime.now(UTC)
    files = [
        _version_file(
            owner_id=owner.id,
            lineage_id=lineage_id,
            version=version,
            created_at=base + timedelta(seconds=version),
        )
        for version in (1, 2, 3)
    ]
    await _insert_files(session_factory, files)

    async with session_factory() as session:
        repository = PostgreSQLUserVaultFileRepository(session)
        head = await repository.get_document_head(user_id=owner.id, document_lineage_id=lineage_id)
        assert head is not None and head.document_version == 3
        assert (
            await repository.get_document_head(user_id=stranger.id, document_lineage_id=lineage_id)
            is None
        )
        assert (
            await repository.get_document_head(user_id=owner.id, document_lineage_id=uuid4())
            is None
        )

    async with session_factory() as session, session.begin():
        model = await session.get(UserVaultFileModel, files[2].id)
        assert model is not None
        model.deleted_at = base + timedelta(minutes=1)

    async with session_factory() as session:
        head = await PostgreSQLUserVaultFileRepository(session).get_document_head(
            user_id=owner.id, document_lineage_id=lineage_id
        )
    assert head is not None and head.document_version == 2


async def test_list_document_heads_returns_one_head_per_workspace_lineage(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await _create_owner(session_factory)
    older_lineage, newer_lineage, foreign_lineage, wildcard_lineage = (
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
    )
    base = datetime.now(UTC)
    await _insert_files(
        session_factory,
        [
            _version_file(owner_id=owner.id, lineage_id=older_lineage, version=1, created_at=base),
            _version_file(
                owner_id=owner.id,
                lineage_id=older_lineage,
                version=2,
                created_at=base + timedelta(seconds=1),
            ),
            _version_file(
                owner_id=owner.id,
                lineage_id=newer_lineage,
                version=1,
                created_at=base + timedelta(seconds=5),
            ),
            _version_file(
                owner_id=owner.id,
                lineage_id=foreign_lineage,
                version=1,
                created_at=base,
                source_artifact_id=f"other.app:exam-workspace:{foreign_lineage}:v1",
            ),
            # `_` in the prefix must match literally, not as a LIKE wildcard.
            _version_file(
                owner_id=owner.id,
                lineage_id=wildcard_lineage,
                version=1,
                created_at=base,
                source_artifact_id=f"documents.conversionXhub:exam-workspace:{wildcard_lineage}:v1",
            ),
        ],
    )

    async with session_factory() as session:
        heads = await PostgreSQLUserVaultFileRepository(session).list_document_heads(
            user_id=owner.id, source_artifact_prefix=_WORKSPACE_PREFIX
        )

    assert [(head.document_lineage_id, head.document_version) for head in heads] == [
        (newer_lineage, 1),
        (older_lineage, 2),
    ]


async def test_duplicate_document_version_maps_to_conflict_without_writing_a_file(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """A second save of an existing (lineage, version) is refused before storage.

    ``create()`` flushes the row before the content is stored, so the unique
    index raises on the duplicate before any file is written. Verified: the
    duplicate maps to CONFLICT, no file exists for the duplicate id, and the
    first version's file, row, and usage total are intact.
    """
    owner = await _create_owner(session_factory)
    lineage_id = uuid4()
    storage = LocalVaultStorage(vault_root=tmp_path)
    settings = Settings.model_construct(
        VAULT_MAX_FILE_BYTES=1_000_000, VAULT_MAX_TOTAL_BYTES=10_000_000
    )

    async def save(file_id: UUID) -> VaultFile:
        async with session_factory() as session:
            store = ExamWorkspaceDocumentStore(
                vault_files=PostgreSQLUserVaultFileRepository(session),
                vault_usage=PostgreSQLUserVaultUsageRepository(session),
                vault_storage=storage,
                uow=SQLAlchemyUnitOfWork(session),
                clock=FixedClock(datetime.now(UTC)),
                settings=settings,
                proposal_carry_forward=CarryExamWorkspaceProposals(
                    enrichment_jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
                    proposed_overlays=PostgreSQLExamAnswerKeyProposedOverlayRepository(session),
                    clock=FixedClock(datetime.now(UTC)),
                    id_generator=UUIDGenerator(),
                ),
            )
            return await store.save_version(
                actor=owner,
                file_id=file_id,
                name="prov.provdokument.zip",
                content=b"container-bytes",
                lineage_id=lineage_id,
                version=1,
            )

    first = await save(uuid4())
    duplicate_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        await save(duplicate_id)

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert exc_info.value.details == {"lineage_id": str(lineage_id), "version": 1}
    assert await storage.exists_file(user_id=owner.id, file_id=first.id)
    assert not await storage.exists_file(user_id=owner.id, file_id=duplicate_id)
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(UserVaultFileModel)
            .where(UserVaultFileModel.document_lineage_id == lineage_id)
        )
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=owner.id)
    assert count == 1
    assert usage is not None and usage.bytes_total == len(b"container-bytes")


async def _create_conversion_job(
    session_factory: async_sessionmaker[AsyncSession], owner_id: UUID
) -> ConversionHubJob:
    now = datetime.now(UTC)
    candidate = ConversionHubJob(
        id=uuid4(),
        owner_user_id=owner_id,
        input_filename="exam.dxe",
        source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
        output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        status=ConversionHubJobStatus.SUBMITTED,
        submission_idempotency_key=f"workspace-test-{uuid4()}",
        created_at=now,
        updated_at=now,
    )
    async with session_factory() as session, session.begin():
        job, _ = await PostgreSQLConversionHubJobRepository(
            session
        ).acquire_by_owner_and_submission_key(job=candidate)
    return job


async def test_workspace_enrichment_jobs_are_unique_per_lineage_revision(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await _create_owner(session_factory)
    lineage_id = uuid4()
    now = datetime.now(UTC)

    def workspace_job(revision: int) -> ExamAnswerKeyEnrichmentJob:
        return enqueue_workspace_enrichment_job(
            job_id=uuid4(),
            owner_user_id=owner.id,
            input_filename="prov.provdokument.zip",
            workspace_lineage_id=lineage_id,
            workspace_document_revision=revision,
            now=now,
        )

    revision_one = workspace_job(1)
    async with session_factory() as session, session.begin():
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        await repository.create(job=revision_one)
        await repository.create(job=workspace_job(2))

    async with session_factory() as session:
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        found = await repository.get_by_workspace_revision(
            owner_user_id=owner.id,
            workspace_lineage_id=lineage_id,
            workspace_document_revision=1,
        )
        assert found is not None and found.id == revision_one.id
        assert (
            await repository.get_by_workspace_revision(
                owner_user_id=owner.id,
                workspace_lineage_id=lineage_id,
                workspace_document_revision=3,
            )
            is None
        )
        assert (
            await repository.get_by_workspace_revision(
                owner_user_id=uuid4(),
                workspace_lineage_id=lineage_id,
                workspace_document_revision=1,
            )
            is None
        )

    with pytest.raises(IntegrityError) as exc_info:
        async with session_factory() as session, session.begin():
            await PostgreSQLExamAnswerKeyEnrichmentJobRepository(session).create(
                job=workspace_job(1)
            )
    assert "uq_exam_answer_key_enrichment_jobs_workspace_revision" in str(exc_info.value)


async def test_dxe_enrichment_jobs_are_outside_the_workspace_unique_index(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await _create_owner(session_factory)
    now = datetime.now(UTC)
    conversion_jobs = [await _create_conversion_job(session_factory, owner.id) for _ in range(2)]

    dxe_jobs = [
        enqueue_enrichment_job(
            job_id=uuid4(),
            conversion_job_id=conversion_job.id,
            owner_user_id=owner.id,
            input_filename="exam.dxe",
            source_dxe=b"dxe",
            now=now,
        )
        for conversion_job in conversion_jobs
    ]
    async with session_factory() as session, session.begin():
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        for dxe_job in dxe_jobs:
            await repository.create(job=dxe_job)

    async with session_factory() as session:
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        for dxe_job in dxe_jobs:
            stored = await repository.get_by_id(job_id=dxe_job.id)
            assert stored is not None
            assert stored.workspace_lineage_id is None
            assert stored.workspace_document_revision is None


@pytest.mark.parametrize(
    "scenario", ["pending", "rejected", "teacher_authored", "reviewed_advisory", "stale", "deleted"]
)
async def test_workspace_save_persists_only_pending_overlay_and_preserves_previous_revision(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path, scenario: str
) -> None:
    owner = await _create_owner(session_factory)
    document = proposal_document()
    now = datetime.now(UTC)
    codec = ExamWorkspaceContainerCodec()
    storage = LocalVaultStorage(vault_root=tmp_path)
    original_bytes = codec.build(content=ExamWorkspaceContainerContent(document=document))
    original_file_id = uuid4()
    job, overlay = proposal_ledger(owner_user_id=owner.id, document=document, now=now)

    async with session_factory() as session:
        files = PostgreSQLUserVaultFileRepository(session)
        jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        overlays = PostgreSQLExamAnswerKeyProposedOverlayRepository(session)
        store = _proposal_store(session, storage)
        await store.save_version(
            actor=owner,
            file_id=original_file_id,
            name="exam.provdokument.zip",
            content=original_bytes,
            lineage_id=document.document_id,
            version=1,
        )
        async with SQLAlchemyUnitOfWork(session):
            await jobs.create(job=job)
            await overlays.create(proposed_overlay=overlay)
        await SaveExamWorkspaceDocumentHandler(
            vault_files=files, codec=codec, store=store, id_generator=UUIDGenerator()
        ).handle(
            actor=owner,
            lineage_id=document.document_id,
            request=SaveExamWorkspaceDocumentRequest(
                expected_revision=1,
                document=saved_proposal_document(document, scenario),
                rejected_proposal_item_ids=("item_001",) if scenario == "rejected" else (),
            ),
        )

    # A fresh session proves committed revision lookup and immutable old records.
    async with session_factory() as session:
        files = PostgreSQLUserVaultFileRepository(session)
        jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        overlays = PostgreSQLExamAnswerKeyProposedOverlayRepository(session)
        carried_job = await jobs.get_by_workspace_revision(
            owner_user_id=owner.id,
            workspace_lineage_id=document.document_id,
            workspace_document_revision=2,
        )
        assert await jobs.get_by_id(job_id=job.id) == job
        assert await overlays.get_by_enrichment_job_id(enrichment_job_id=job.id) == overlay
        assert await storage.read_file(user_id=owner.id, file_id=original_file_id) == original_bytes
        head = await files.get_document_head(
            user_id=owner.id, document_lineage_id=document.document_id
        )
        assert head is not None and head.document_version == 2
        saved = codec.parse(content=await storage.read_file(user_id=owner.id, file_id=head.id))
        assert saved.document == saved_proposal_document(document, scenario)
        status = await GetExamWorkspaceEnrichmentStatusHandler(
            vault_files=files,
            enrichment_jobs=jobs,
            proposed_overlays=overlays,
            store=_proposal_store(session, storage),
            codec=codec,
        ).handle(actor=owner, lineage_id=document.document_id)
        assert [proposal.item_id for proposal in status.proposals] == (
            ["item_001"] if scenario == "pending" else []
        )
        if scenario == "pending":
            assert carried_job is not None and carried_job.id != job.id
            assert carried_job.attempts == 0 and carried_job.started_at is None
            carried_overlay = await overlays.get_by_enrichment_job_id(
                enrichment_job_id=carried_job.id
            )
            assert carried_overlay is not None and carried_overlay.id != overlay.id
            assert carried_overlay.source_file_sha256 == overlay.source_file_sha256
            assert carried_overlay.source_ir_sha256 == overlay.source_ir_sha256
            assert carried_overlay.overlay_json["document_revision"] == 2
        else:
            assert carried_job is None


def _proposal_store(
    session: AsyncSession, storage: LocalVaultStorage, ids: SequenceIdGenerator | None = None
) -> ExamWorkspaceDocumentStore:
    return ExamWorkspaceDocumentStore(
        vault_files=PostgreSQLUserVaultFileRepository(session),
        vault_usage=PostgreSQLUserVaultUsageRepository(session),
        vault_storage=storage,
        uow=SQLAlchemyUnitOfWork(session),
        clock=FixedClock(datetime.now(UTC)),
        settings=Settings.model_construct(
            VAULT_MAX_FILE_BYTES=1_000_000, VAULT_MAX_TOTAL_BYTES=10_000_000
        ),
        proposal_carry_forward=CarryExamWorkspaceProposals(
            enrichment_jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
            proposed_overlays=PostgreSQLExamAnswerKeyProposedOverlayRepository(session),
            clock=FixedClock(datetime.now(UTC)),
            id_generator=ids or UUIDGenerator(),
        ),
    )


async def test_overlay_failure_rolls_back_document_job_usage_and_storage(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    owner = await _create_owner(session_factory)
    document = proposal_document()
    now = datetime.now(UTC)
    codec = ExamWorkspaceContainerCodec()
    storage = LocalVaultStorage(vault_root=tmp_path)
    original_bytes = codec.build(content=ExamWorkspaceContainerContent(document=document))
    job, overlay = proposal_ledger(owner_user_id=owner.id, document=document, now=now)
    new_file_id, new_job_id = uuid4(), uuid4()
    async with session_factory() as session:
        store = _proposal_store(session, storage)
        await store.save_version(
            actor=owner,
            file_id=uuid4(),
            name="exam.provdokument.zip",
            content=original_bytes,
            lineage_id=document.document_id,
            version=1,
        )
        async with SQLAlchemyUnitOfWork(session):
            await PostgreSQLExamAnswerKeyEnrichmentJobRepository(session).create(job=job)
            await PostgreSQLExamAnswerKeyProposedOverlayRepository(session).create(
                proposed_overlay=overlay
            )
        # Force an overlay primary-key collision after the new file/job are flushed.
        failing_store = _proposal_store(
            session, storage, SequenceIdGenerator([new_job_id, overlay.id])
        )
        with pytest.raises(DomainError) as exc_info:
            await SaveExamWorkspaceDocumentHandler(
                vault_files=PostgreSQLUserVaultFileRepository(session),
                codec=codec,
                store=failing_store,
                id_generator=SequenceIdGenerator([new_file_id]),
            ).handle(
                actor=owner,
                lineage_id=document.document_id,
                request=SaveExamWorkspaceDocumentRequest(
                    expected_revision=1, document=document.with_revision(2)
                ),
            )
        assert exc_info.value.code is ErrorCode.CONFLICT

    async with session_factory() as session:
        head = await PostgreSQLUserVaultFileRepository(session).get_document_head(
            user_id=owner.id, document_lineage_id=document.document_id
        )
        assert head is not None and head.document_version == 1
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=owner.id)
        assert usage is not None and usage.bytes_total == len(original_bytes)
        assert (
            await PostgreSQLExamAnswerKeyEnrichmentJobRepository(session).get_by_id(
                job_id=new_job_id
            )
            is None
        )
        assert (
            await PostgreSQLExamAnswerKeyProposedOverlayRepository(
                session
            ).get_by_enrichment_job_id(enrichment_job_id=job.id)
            == overlay
        )
    assert not await storage.exists_file(user_id=owner.id, file_id=new_file_id)
