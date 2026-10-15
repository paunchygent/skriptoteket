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
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.db.models.user_vault_file import UserVaultFileModel
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
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
from tests.integration.exam_workspace_conversion_support import (
    SETTINGS,
    WORKER,
    ConversionWorld,
    Ids,
    batch,
)
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


async def test_batches_replace_their_placeholders_keep_teacher_edits_and_hold_one_copy(
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
            settings=SETTINGS,
            id_generator=Ids(),
        ).handle(actor=actor, filename="prov.docx", content=b"docx-bytes")
        world = ConversionWorld(session, storage, clock)
        async with world.uow:
            claimed = await world.jobs.claim_next(
                worker_id=WORKER,
                now=now,
                lease_ttl=timedelta(minutes=15),
                source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
            )
        assert claimed is not None
        lineage_id = queued.lineage_id

        await world.progress.outline(
            worker_id=WORKER,
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
            worker_id=WORKER, job_id=queued.job_id, update=batch(lineage_id, q2=None, q3=None)
        )
        first = await world.open(actor, lineage_id)
        assert first.revision == 1
        assert _texts(first) == ["Fråga ett", "Källtext två", "Källtext tre"]

        # A worker that no longer owns the lease writes nothing.
        await world.progress.batch_ready(
            worker_id="stale-worker",
            job_id=queued.job_id,
            update=batch(lineage_id, q2="Fel", q3="Fel"),
        )
        assert (await world.open(actor, lineage_id)).revision == 1

    # In another session the teacher opens the unfinished exam: the response names the
    # running conversion and the placeholders it still owns.
    async with session_factory() as teacher_session:
        teacher = ConversionWorld(teacher_session, storage, clock)
        response = await teacher.opened(actor, lineage_id)
        opened = response.document
        assert response.conversion is not None
        assert (response.conversion.state, response.conversion.document_revision) == ("running", 1)
        assert {
            unit.unit_id: (unit.state, unit.item_ids) for unit in response.conversion.units
        } == {
            "q1": ("ready", ("item_001",)),
            "q2": ("converting", ("item_002",)),
            "q3": ("converting", ("item_003",)),
        }
        q1 = opened.items[0].model_copy(update={"body": body("Lärarens fråga ett")})
        q2 = opened.items[1].model_copy(
            update={"body": body("Lärarens fråga två"), "title": "Lärarens rubrik"}
        )
        # A save that also rewrites the q2 placeholder is refused and stores nothing.
        with pytest.raises(DomainError) as refused:
            await teacher.teacher_save(
                actor, opened.model_copy(update={"items": (q1, q2, opened.items[2])})
            )
        assert refused.value.code is ErrorCode.VALIDATION_ERROR
        assert refused.value.details["item_ids"] == ["item_002"]
        assert (await teacher.open(actor, lineage_id)).revision == 1
        # The same edit of converted q1 alone saves revision 2.
        saved = await teacher.teacher_save(
            actor, opened.model_copy(update={"items": (q1, *opened.items[1:])})
        )
        assert saved.document.revision == 2
        assert saved.conversion is not None and saved.conversion.document_revision == 1

    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        await world.progress.batch_ready(
            worker_id=WORKER,
            job_id=queued.job_id,
            update=batch(lineage_id, q2="Fråga två", q3=None),
        )
        # q2's batch replaces its placeholder; the teacher's q1 stays.
        third = await world.open(actor, lineage_id)
        assert third.revision == 3
        assert _texts(third) == ["Lärarens fråga ett", "Fråga två", "Källtext tre"]
        assert third.items[1].kind is NativeExamItemKind.SINGLE_CHOICE

        await world.progress.batch_ready(
            worker_id=WORKER,
            job_id=queued.job_id,
            update=batch(lineage_id, q2="Fråga två", q3="Fråga tre"),
        )
        fourth = await world.open(actor, lineage_id)
        assert _texts(fourth) == ["Lärarens fråga ett", "Fråga två", "Fråga tre"]
        status = await world.status.handle(actor=actor, job_id=queued.job_id)
        assert (status.document_revision, status.questions_done) == (4, 3)
        assert {unit.unit_id: unit.state for unit in status.units} == {
            "q1": "ready",
            "q2": "ready",
            "q3": "ready",
        }

    # Revisions the teacher saved on (1, the base of their save, and 2, their own) stay;
    # conversion-only revision 3 was superseded by revision 4, so it is retired.
    live = await _live_versions(session_factory, lineage_id)
    assert [version for version, _ in live] == [1, 2, 4]
    assert await _usage(session_factory, actor) == sum(size for _, size in live)

    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        file_id = uuid4()
        async with world.uow:
            await world.progress.publish_final(
                worker_id=WORKER,
                job_id=queued.job_id,
                lineage_id=lineage_id,
                actor=actor,
                file_id=file_id,
                name="prov.provdokument.zip",
                update=batch(lineage_id, q2="Fråga två", q3="Fråga tre slutlig"),
                notes=("Facit: 1 Ja",),
            )
        final = await world.open(actor, lineage_id)
        assert _texts(final) == ["Lärarens fråga ett", "Fråga två", "Fråga tre slutlig"]

    # Conversion-only revision 4 was superseded by the final revision 5, so it is retired.
    live = await _live_versions(session_factory, lineage_id)
    assert [version for version, _ in live] == [1, 2, 5]
    assert await _usage(session_factory, actor) == sum(size for _, size in live)


async def test_saves_that_remove_or_take_over_a_placeholder_are_refused(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    """The review's probe scenarios: each save is refused, so the batch lands intact."""
    actor = await create_owner(session_factory)
    now = datetime.now(UTC)
    clock = FixedClock(now)
    storage = LocalVaultStorage(vault_root=tmp_path)

    def sectioned(*, q2: str | None, q3: str | None) -> ConversionUpdate:
        return conversion_update(
            [
                ("q1", [choice("p1", "Fråga ett")]),
                ("q2", [choice("p2", q2)] if q2 else [placeholder("p2", "Källtext två")]),
                ("q3", [choice("p3", q3)] if q3 else [placeholder("p3", "Källtext tre")]),
            ],
            pending=tuple(q for q, done in (("q2", q2), ("q3", q3)) if not done),
            parents=(("section", ("q1", "q2", "q3")),),
            document_id=lineage_id,
        )

    async with session_factory() as session:
        queued = await ImportExamWorkspaceDocumentHandler(
            jobs=PostgreSQLExamAnswerKeyEnrichmentJobRepository(session),
            uow=SQLAlchemyUnitOfWork(session),
            clock=clock,
            settings=SETTINGS,
            id_generator=Ids(),
        ).handle(actor=actor, filename="prov.docx", content=b"docx-bytes")
        lineage_id = queued.lineage_id
        world = ConversionWorld(session, storage, clock)
        async with world.uow:
            await world.jobs.claim_next(
                worker_id=WORKER,
                now=now,
                lease_ttl=timedelta(minutes=15),
                source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
            )
        await world.progress.batch_ready(
            worker_id=WORKER, job_id=queued.job_id, update=sectioned(q2=None, q3=None)
        )

    async with session_factory() as teacher_session:
        teacher = ConversionWorld(teacher_session, storage, clock)
        opened = await teacher.open(actor, lineage_id)
        q1, q2, q3 = opened.items
        section = opened.parents[0]

        # Probe 1: delete the middle placeholder and its membership in the section.
        kept = (q1, q3.model_copy(update={"sequence": 2}))
        without_q2 = opened.model_copy(
            update={
                "items": kept,
                "parents": (section.model_copy(update={"item_ids": (q1.item_id, q3.item_id)}),),
            }
        )
        with pytest.raises(DomainError) as deleted:
            await teacher.teacher_save(actor, NativeExamDocument.model_validate(without_q2))
        assert deleted.value.details["item_ids"] == [q2.item_id]

        # Probe 2: delete the last placeholder and give its id to a new teacher question.
        teacher_question = q3.model_copy(
            update={
                "body": body("Lärarens nya fråga"),
                "source_anchor": None,
                "review": q3.review.model_copy(
                    update={"parse_origin": NativeParseOrigin.TEACHER_CREATED, "reasons": ()}
                ),
            }
        )
        reused = opened.model_copy(
            update={
                "items": (q1, q2, teacher_question),
                "parents": (section.model_copy(update={"item_ids": (q1.item_id, q2.item_id)}),),
            }
        )
        with pytest.raises(DomainError) as taken_over:
            await teacher.teacher_save(actor, NativeExamDocument.model_validate(reused))
        assert taken_over.value.details["item_ids"] == [q3.item_id]

        # Adding a question after the placeholders and editing converted q1 is allowed.
        added = teacher_question.model_copy(update={"item_id": "item_004", "sequence": 4})
        edited = q1.model_copy(update={"body": body("Lärarens fråga ett")})
        await teacher.teacher_save(
            actor, opened.model_copy(update={"items": (edited, q2, q3, added)})
        )

    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        await world.progress.batch_ready(
            worker_id=WORKER,
            job_id=queued.job_id,
            update=sectioned(q2="Fråga två", q3="Fråga tre"),
        )
        final = await world.open(actor, lineage_id)
        assert _texts(final) == [
            "Lärarens fråga ett",
            "Fråga två",
            "Fråga tre",
            "Lärarens nya fråga",
        ]
        assert [parent.item_ids for parent in final.parents] == [
            tuple(item.item_id for item in final.items[:3])
        ]
