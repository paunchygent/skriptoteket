"""PostgreSQL coverage for exam workspace persistence seams (TASK-SKRIPT-39-04-01).

Covers the one-file Mina filer exam document (head lookup, head listing, the
stale-revision CONFLICT path and the overwrite that preserves the row) and
workspace-kind answer-key enrichment jobs (revision lookup and the partial
unique index that leaves DXE jobs unconstrained).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX,
    ExamWorkspaceDocumentStore,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.conversion_hub_jobs import (
    PostgreSQLConversionHubJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_index_repository import (
    PostgreSQLExamIndexRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.exam_workspace_test_support import (
    create_owner,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

_WORKSPACE_PREFIX = f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:"


def _exam_file(
    *,
    owner_id: UUID,
    lineage_id: UUID,
    version: int,
    created_at: datetime,
    export_format: str | None = None,
    deleted_at: datetime | None = None,
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
        or f"{EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX}:{lineage_id}"
        + (f":{export_format}" if export_format else ""),
        document_lineage_id=lineage_id,
        document_version=version,
        export_format=export_format,
        created_at=created_at,
        deleted_at=deleted_at,
    )


async def _insert_files(
    session_factory: async_sessionmaker[AsyncSession], files: list[VaultFile]
) -> None:
    async with session_factory() as session, session.begin():
        repository = PostgreSQLUserVaultFileRepository(session)
        for file in files:
            await repository.create(file=file)


async def _save_document(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    actor: User,
    storage: LocalVaultStorage,
    settings: Settings,
    lineage_id: UUID,
    file_id: UUID,
    content: bytes,
    version: int,
    expected_revision: int | None,
) -> VaultFile:
    async with session_factory() as session:
        store = ExamWorkspaceDocumentStore(
            vault_files=PostgreSQLUserVaultFileRepository(session),
            vault_usage=PostgreSQLUserVaultUsageRepository(session),
            vault_storage=storage,
            index=PostgreSQLExamIndexRepository(session),
            codec=ExamWorkspaceContainerCodec(),
            uow=SQLAlchemyUnitOfWork(session),
            clock=FixedClock(datetime.now(UTC)),
            settings=settings,
        )
        return await store.save(
            actor=actor,
            file_id=file_id,
            name="prov.provdokument.zip",
            content=content,
            lineage_id=lineage_id,
            version=version,
            expected_revision=expected_revision,
            editor_step_id=None if expected_revision is None else lineage_id,
        )


async def test_get_document_head_returns_the_one_active_exam_row_for_its_owner(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await create_owner(session_factory)
    stranger = await create_owner(session_factory)
    lineage_id = uuid4()
    base = datetime.now(UTC)
    exam = _exam_file(owner_id=owner.id, lineage_id=lineage_id, version=2, created_at=base)
    trashed = _exam_file(
        owner_id=owner.id,
        lineage_id=lineage_id,
        version=1,
        created_at=base,
        deleted_at=base + timedelta(minutes=1),
    )
    export = _exam_file(
        owner_id=owner.id,
        lineage_id=lineage_id,
        version=2,
        created_at=base,
        export_format="qti",
    )
    foreign = _exam_file(owner_id=stranger.id, lineage_id=lineage_id, version=1, created_at=base)
    await _insert_files(session_factory, [exam, trashed, export, foreign])

    async with session_factory() as session:
        repository = PostgreSQLUserVaultFileRepository(session)
        head = await repository.get_document_head(user_id=owner.id, document_lineage_id=lineage_id)
        assert head is not None and head.id == exam.id
        foreign_head = await repository.get_document_head(
            user_id=stranger.id, document_lineage_id=lineage_id
        )
        assert foreign_head is not None and foreign_head.id == foreign.id
        assert (
            await repository.get_document_head(user_id=owner.id, document_lineage_id=uuid4())
            is None
        )


async def test_list_document_heads_returns_one_head_per_workspace_lineage(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await create_owner(session_factory)
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
            _exam_file(owner_id=owner.id, lineage_id=older_lineage, version=3, created_at=base),
            # A saved export of the exam is not a document head.
            _exam_file(
                owner_id=owner.id,
                lineage_id=older_lineage,
                version=3,
                created_at=base + timedelta(seconds=2),
                export_format="qti",
            ),
            _exam_file(
                owner_id=owner.id,
                lineage_id=newer_lineage,
                version=1,
                created_at=base + timedelta(seconds=5),
            ),
            _exam_file(
                owner_id=owner.id,
                lineage_id=foreign_lineage,
                version=1,
                created_at=base,
                source_artifact_id=f"other.app:exam-workspace:{foreign_lineage}",
            ),
            # `_` in the prefix must match literally, not as a LIKE wildcard.
            _exam_file(
                owner_id=owner.id,
                lineage_id=wildcard_lineage,
                version=1,
                created_at=base,
                source_artifact_id=f"documents.conversionXhub:exam-workspace:{wildcard_lineage}",
            ),
        ],
    )

    async with session_factory() as session:
        heads = await PostgreSQLUserVaultFileRepository(session).list_document_heads(
            user_id=owner.id, source_artifact_prefix=_WORKSPACE_PREFIX
        )

    assert [(head.document_lineage_id, head.document_version) for head in heads] == [
        (newer_lineage, 1),
        (older_lineage, 3),
    ]


async def test_save_with_stale_expected_revision_is_refused_and_writes_nothing(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """An overwrite guarded by a stale revision is refused before storage.

    The store reads the current row inside the lineage lock, so the revision
    check maps the caller's stale expectation to CONFLICT: no file is written
    and the first save's row, payload and usage total stay intact.
    """
    actor = await create_owner(session_factory)
    lineage_id = uuid4()
    storage = LocalVaultStorage(vault_root=tmp_path)
    settings = Settings.model_construct(
        VAULT_MAX_FILE_BYTES=1_000_000, VAULT_MAX_TOTAL_BYTES=10_000_000
    )

    first = await _save_document(
        session_factory,
        actor=actor,
        storage=storage,
        settings=settings,
        lineage_id=lineage_id,
        file_id=uuid4(),
        content=b"container-bytes",
        version=1,
        expected_revision=None,
    )
    refused_id = uuid4()
    with pytest.raises(DomainError) as exc_info:
        await _save_document(
            session_factory,
            actor=actor,
            storage=storage,
            settings=settings,
            lineage_id=lineage_id,
            file_id=refused_id,
            content=b"stale-container-bytes",
            version=2,
            expected_revision=0,
        )

    assert exc_info.value.code is ErrorCode.CONFLICT
    assert exc_info.value.details == {"expected_revision": 0, "current_revision": 1}
    assert await storage.exists_file(user_id=actor.id, file_id=first.id)
    assert not await storage.exists_file(user_id=actor.id, file_id=refused_id)
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(UserVaultFileModel)
            .where(UserVaultFileModel.document_lineage_id == lineage_id)
        )
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=actor.id)
    assert count == 1
    assert usage is not None and usage.bytes_total == len(b"container-bytes")


async def test_overwriting_an_exam_keeps_the_row_and_adjusts_vault_usage(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    """A current expected_revision overwrites the one exam row instead of adding one."""
    actor = await create_owner(session_factory)
    lineage_id = uuid4()
    storage = LocalVaultStorage(vault_root=tmp_path)
    settings = Settings.model_construct(
        VAULT_MAX_FILE_BYTES=1_000_000, VAULT_MAX_TOTAL_BYTES=10_000_000
    )

    first = await _save_document(
        session_factory,
        actor=actor,
        storage=storage,
        settings=settings,
        lineage_id=lineage_id,
        file_id=uuid4(),
        content=b"container-bytes",
        version=1,
        expected_revision=None,
    )
    unused_id = uuid4()
    second_content = b"a longer container body"
    overwritten = await _save_document(
        session_factory,
        actor=actor,
        storage=storage,
        settings=settings,
        lineage_id=lineage_id,
        file_id=unused_id,
        content=second_content,
        version=2,
        expected_revision=1,
    )

    assert overwritten.id == first.id
    assert overwritten.document_version == 2
    assert overwritten.bytes == len(second_content)
    assert await storage.read_file(user_id=actor.id, file_id=first.id) == second_content
    assert not await storage.exists_file(user_id=actor.id, file_id=unused_id)
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(UserVaultFileModel)
            .where(UserVaultFileModel.document_lineage_id == lineage_id)
        )
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=actor.id)
    assert count == 1
    assert usage is not None and usage.bytes_total == len(second_content)


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


async def test_workspace_suggestion_jobs_coexist_for_one_lineage(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Per-question and per-exam requests are separate jobs on sent content."""
    owner = await create_owner(session_factory)
    lineage_id = uuid4()
    now = datetime.now(UTC)

    def workspace_job() -> ExamAnswerKeyEnrichmentJob:
        return enqueue_workspace_enrichment_job(
            job_id=uuid4(),
            owner_user_id=owner.id,
            input_filename="prov.provdokument.zip",
            workspace_lineage_id=lineage_id,
            workspace_document_revision=3,
            workspace_request_json={"views": []},
            now=now,
        )

    # Both stand on saved revision 3: one exam file carries several jobs.
    first = workspace_job()
    second = workspace_job()
    async with session_factory() as session, session.begin():
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        await repository.create(job=first)
        await repository.create(job=second)

    async with session_factory() as session:
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        found = await repository.get_by_id(job_id=first.id)
        assert found is not None
        assert found.workspace_lineage_id == lineage_id
        assert found.workspace_document_revision == 3
        assert found.workspace_request_json == {"views": []}
        assert await repository.get_by_id(job_id=uuid4()) is None


async def test_dxe_enrichment_jobs_carry_no_workspace_binding(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = await create_owner(session_factory)
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

    async with session_factory() as session, session.begin():
        repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        for dxe_job in dxe_jobs:
            stored = await repository.get_by_id_for_update(job_id=dxe_job.id)
            assert stored is not None
            assert stored.workspace_lineage_id is None
            assert stored.workspace_document_revision is None
