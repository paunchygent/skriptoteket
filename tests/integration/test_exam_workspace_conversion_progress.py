"""Real PostgreSQL proof of progressive DOCX delivery against concurrent teacher saves (D30).

The job queue, vault repositories, container codec, local vault storage and the save
handler are the production implementations; the provisional documents stand in for the
pipeline's batches.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceConversionStatus,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_progress import (
    ExamWorkspaceConversionProgress,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
    GetExamWorkspaceConversionStatusHandler,
    GetExamWorkspaceDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_proposal_carry_forward import (
    CarryExamWorkspaceProposals,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeTextSegment,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_proposed_overlays import (
    PostgreSQLExamAnswerKeyProposedOverlayRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.docx_conversion_progress import (
    ConversionOutline,
    ConversionUpdate,
    OutlineQuestion,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.integration.infrastructure.repositories.exam_workspace_test_support import (
    create_owner,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    body,
    choice,
    conversion_update,
    placeholder,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]

_WORKER = "conversion-worker"
_SETTINGS = Settings.model_construct(
    VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
)


class _Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


class _World:
    def __init__(
        self, session: AsyncSession, storage: LocalVaultStorage, clock: FixedClock
    ) -> None:
        self.uow = SQLAlchemyUnitOfWork(session)
        self.jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        self.vault_files = PostgreSQLUserVaultFileRepository(session)
        self.codec = ExamWorkspaceContainerCodec()
        self.store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=PostgreSQLUserVaultUsageRepository(session),
            vault_storage=storage,
            uow=self.uow,
            clock=clock,
            settings=_SETTINGS,
            proposal_carry_forward=CarryExamWorkspaceProposals(
                enrichment_jobs=self.jobs,
                proposed_overlays=PostgreSQLExamAnswerKeyProposedOverlayRepository(session),
                clock=clock,
                id_generator=_Ids(),
            ),
        )
        self.progress = ExamWorkspaceConversionProgress(
            jobs=self.jobs,
            users=PostgreSQLUserRepository(session),
            vault_files=self.vault_files,
            store=self.store,
            codec=self.codec,
            uow=self.uow,
            clock=clock,
            id_generator=_Ids(),
        )
        self.status = GetExamWorkspaceConversionStatusHandler(jobs=self.jobs)

    async def open(self, actor: User, lineage_id: UUID) -> NativeExamDocument:
        response = await GetExamWorkspaceDocumentHandler(
            vault_files=self.vault_files, codec=self.codec, store=self.store
        ).handle(actor=actor, lineage_id=lineage_id)
        return response.document

    async def teacher_save(self, actor: User, document: NativeExamDocument) -> None:
        await SaveExamWorkspaceDocumentHandler(
            vault_files=self.vault_files, codec=self.codec, store=self.store, id_generator=_Ids()
        ).handle(
            actor=actor,
            lineage_id=document.document_id,
            request=SaveExamWorkspaceDocumentRequest(
                expected_revision=document.revision,
                document=document.model_copy(update={"revision": document.revision + 1}),
            ),
        )


def _texts(document: NativeExamDocument) -> list[str]:
    return [
        "".join(s.text for s in item.body[0].segments if isinstance(s, NativeTextSegment))
        for item in document.items
    ]


async def _live_versions(
    session_factory: async_sessionmaker[AsyncSession], lineage_id: UUID
) -> list[tuple[int, int]]:
    async with session_factory() as session:
        rows = await session.execute(
            select(UserVaultFileModel.document_version, UserVaultFileModel.bytes)
            .where(UserVaultFileModel.document_lineage_id == lineage_id)
            .where(UserVaultFileModel.deleted_at.is_(None))
            .order_by(UserVaultFileModel.document_version)
        )
        return [(version, size) for version, size in rows.all()]


async def _usage(session_factory: async_sessionmaker[AsyncSession], actor: User) -> int:
    async with session_factory() as session:
        usage = await PostgreSQLUserVaultUsageRepository(session).get(user_id=actor.id)
        return 0 if usage is None else usage.bytes_total


def _batch(lineage_id: UUID, *, q2: str | None, q3: str | None) -> ConversionUpdate:
    return conversion_update(
        [
            ("q1", [choice("p1", "Fråga ett")]),
            ("q2", [choice("p2", q2)] if q2 else [placeholder("p2", "Källtext två")]),
            ("q3", [choice("p3", q3)] if q3 else [placeholder("p3", "Källtext tre")]),
        ],
        pending=tuple(q for q, done in (("q2", q2), ("q3", q3)) if not done),
        document_id=lineage_id,
    )


async def test_batches_fill_placeholders_teacher_edits_win_and_usage_holds_one_conversion_copy(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    clock = FixedClock(now)
    storage = LocalVaultStorage(vault_root=tmp_path)

    async with session_factory() as session:
        queued = await ImportExamWorkspaceDocumentHandler(
            jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
            uow=SQLAlchemyUnitOfWork(session),
            clock=clock,
            settings=_SETTINGS,
            id_generator=_Ids(),
        ).handle(actor=actor, filename="prov.docx", content=b"docx-bytes")
        world = _World(session, storage, clock)
        async with world.uow:
            claimed = await world.jobs.claim_next(
                worker_id=_WORKER,
                now=now,
                lease_ttl=timedelta(minutes=15),
                source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
            )
        assert claimed is not None
        lineage_id = queued.lineage_id

        await world.progress.outline(
            worker_id=_WORKER,
            job_id=queued.job_id,
            outline=ConversionOutline(
                title=None,
                questions=tuple(
                    OutlineQuestion(
                        question_id=q, position=i, anchors=(f"p{i + 1}",), source_text=q
                    )
                    for i, q in enumerate(("q1", "q2", "q3"))
                ),
            ),
        )
        before_first: ExamWorkspaceConversionStatus = await world.status.handle(
            actor=actor, job_id=queued.job_id
        )
        assert (before_first.document_revision, before_first.questions_done) == (None, 0)
        assert before_first.questions_total == 3 and before_first.units == ()

        # First batch: revision 1 holds q1 and placeholders for q2 and q3.
        await world.progress.batch_ready(
            worker_id=_WORKER, job_id=queued.job_id, update=_batch(lineage_id, q2=None, q3=None)
        )
        first = await world.open(actor, lineage_id)
        assert first.revision == 1
        assert _texts(first) == ["Fråga ett", "Källtext två", "Källtext tre"]

        # A worker that no longer owns the lease writes nothing.
        await world.progress.batch_ready(
            worker_id="stale-worker",
            job_id=queued.job_id,
            update=_batch(lineage_id, q2="Fel", q3="Fel"),
        )
        assert (await world.open(actor, lineage_id)).revision == 1

    # The teacher rewrites the q2 placeholder in another session and saves revision 2.
    async with session_factory() as teacher_session:
        teacher = _World(teacher_session, storage, clock)
        opened = await teacher.open(actor, lineage_id)
        edited = opened.items[1].model_copy(update={"body": body("Lärarens fråga två")})
        await teacher.teacher_save(
            actor, opened.model_copy(update={"items": (opened.items[0], edited, opened.items[2])})
        )

    async with session_factory() as session:
        world = _World(session, storage, clock)
        await world.progress.batch_ready(
            worker_id=_WORKER,
            job_id=queued.job_id,
            update=_batch(lineage_id, q2="Fråga två", q3=None),
        )
        # q2's late result is dropped and nothing else changed, so no revision is written.
        third = await world.open(actor, lineage_id)
        assert third.revision == 2
        assert _texts(third) == ["Fråga ett", "Lärarens fråga två", "Källtext tre"]

        await world.progress.batch_ready(
            worker_id=_WORKER,
            job_id=queued.job_id,
            update=_batch(lineage_id, q2="Fråga två", q3="Fråga tre"),
        )
        fourth = await world.open(actor, lineage_id)
        assert _texts(fourth) == ["Fråga ett", "Lärarens fråga två", "Fråga tre"]
        status = await world.status.handle(actor=actor, job_id=queued.job_id)
        assert (status.document_revision, status.questions_done) == (3, 3)
        assert {unit.unit_id: unit.state for unit in status.units} == {
            "q1": "ready",
            "q2": "teacher_kept",
            "q3": "ready",
        }

    # Revisions the teacher saved on (1, the base of their save, and 2, their own) stay.
    live = await _live_versions(session_factory, lineage_id)
    assert [version for version, _ in live] == [1, 2, 3]
    assert await _usage(session_factory, actor) == sum(size for _, size in live)

    async with session_factory() as session:
        world = _World(session, storage, clock)
        file_id = uuid4()
        async with world.uow:
            await world.progress.publish_final(
                worker_id=_WORKER,
                job_id=queued.job_id,
                lineage_id=lineage_id,
                actor=actor,
                file_id=file_id,
                name="prov.provdokument.zip",
                update=_batch(lineage_id, q2="Fråga två", q3="Fråga tre slutlig"),
                notes=("Facit: 1 Ja",),
            )
        final = await world.open(actor, lineage_id)
        assert _texts(final) == ["Fråga ett", "Lärarens fråga två", "Fråga tre slutlig"]

    # Conversion-only revision 3 was superseded by the final revision 4, so it is retired.
    live = await _live_versions(session_factory, lineage_id)
    assert [version for version, _ in live] == [1, 2, 4]
    assert await _usage(session_factory, actor) == sum(size for _, size in live)
