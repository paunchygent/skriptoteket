"""PostgreSQL coverage for the exam workspace save transaction (TASK-SKRIPT-39-04-04).

Covers carry-forward of pending answer-key proposals when a workspace document
is saved: only a still-pending overlay is copied to the new revision while the
previous revision's job, overlay, and file stay intact, and an overlay write
failure rolls back the new document version, enrichment job, vault usage, and
stored file together.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_workspace import SaveExamWorkspaceDocumentRequest
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
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
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
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
from tests.integration.infrastructure.repositories.exam_workspace_test_support import (
    create_owner,
)
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    UUIDGenerator,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_document_test_support import (
    with_next_revision,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]


@pytest.mark.parametrize(
    "scenario", ["pending", "rejected", "teacher_authored", "reviewed_advisory", "stale", "deleted"]
)
async def test_workspace_save_persists_only_pending_overlay_and_preserves_previous_revision(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path, scenario: str
) -> None:
    owner = await create_owner(session_factory)
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
            vault_files=files, codec=codec, store=store, id_generator=UUIDGenerator(), jobs=jobs
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
        assert await jobs.get_by_id_for_update(job_id=job.id) == job
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
    owner = await create_owner(session_factory)
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
                jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
            ).handle(
                actor=owner,
                lineage_id=document.document_id,
                request=SaveExamWorkspaceDocumentRequest(
                    expected_revision=1, document=with_next_revision(document)
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
            await PostgreSQLExamAnswerKeyEnrichmentJobRepository(session).get_by_id_for_update(
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


async def test_unreadable_overlay_fails_the_save_and_rolls_back_document_and_storage(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    owner = await create_owner(session_factory)
    document = proposal_document()
    now = datetime.now(UTC)
    codec = ExamWorkspaceContainerCodec()
    storage = LocalVaultStorage(vault_root=tmp_path)
    original_bytes = codec.build(content=ExamWorkspaceContainerContent(document=document))
    job, overlay = proposal_ledger(owner_user_id=owner.id, document=document, now=now)
    unreadable = overlay.model_copy(update={"overlay_json": {"items": "unreadable"}})
    new_file_id = uuid4()
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
                proposed_overlay=unreadable
            )
        # A persisted overlay that no longer hydrates fails the save instead of
        # committing a revision that silently lost its pending proposals.
        with pytest.raises(ValidationError):
            await SaveExamWorkspaceDocumentHandler(
                vault_files=PostgreSQLUserVaultFileRepository(session),
                codec=codec,
                store=store,
                id_generator=SequenceIdGenerator([new_file_id]),
                jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
            ).handle(
                actor=owner,
                lineage_id=document.document_id,
                request=SaveExamWorkspaceDocumentRequest(
                    expected_revision=1, document=with_next_revision(document)
                ),
            )

    async with session_factory() as session:
        head = await PostgreSQLUserVaultFileRepository(session).get_document_head(
            user_id=owner.id, document_lineage_id=document.document_id
        )
        assert head is not None and head.document_version == 1
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=owner.id)
        assert usage is not None and usage.bytes_total == len(original_bytes)
        assert (
            await PostgreSQLExamAnswerKeyEnrichmentJobRepository(session).get_by_workspace_revision(
                owner_user_id=owner.id,
                workspace_lineage_id=document.document_id,
                workspace_document_revision=2,
            )
            is None
        )
    assert not await storage.exists_file(user_id=owner.id, file_id=new_file_id)
