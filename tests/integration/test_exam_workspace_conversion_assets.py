"""Real PostgreSQL proof that converted DOCX pictures survive every overwrite (D2).

The job queue, vault repositories, container codec, local vault storage and the save handler
are the production implementations; the provisional batches stand in for the pipeline.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import asset_id_for
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
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

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]

_PICTURE = b"provisional-picture-bytes"
_PICTURE_ID = asset_id_for(_PICTURE)


def _picture_batch(lineage_id: UUID, *, q2: str | None, q3: str | None) -> ConversionUpdate:
    """A batch whose q1 item carries the source picture, payloads included."""
    update = batch(lineage_id, q2=q2, q3=q3)
    first = update.document.items[0]
    item = first.model_copy(
        update={
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Fråga ett", marks=()),
                        NativeAssetSegment(asset_id=_PICTURE_ID),
                    ),
                ),
            )
        }
    )
    asset = NativeExamAsset(
        asset_id=_PICTURE_ID,
        sha256=sha256(_PICTURE).hexdigest(),
        media_type="image/png",
        byte_length=len(_PICTURE),
    )
    document = update.document.model_copy(
        update={"items": (item, *update.document.items[1:]), "assets": (asset,)}
    )
    return replace(update, document=document, assets_by_id={_PICTURE_ID: _PICTURE})


async def test_a_picture_survives_provisional_saves_and_later_batches(
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
        ).handle(actor=actor, filename="prov.docx", content=b"docx-bytes", course_key=None)
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
        # First batch: the picture lands in revision 1 with its payload beside it.
        await world.progress.batch_ready(
            worker_id=WORKER,
            job_id=queued.job_id,
            update=_picture_batch(lineage_id, q2=None, q3=None),
            notes=(),
        )
        first = await world.open(actor, lineage_id)
        assert first.items[0].body_asset_ids() == (_PICTURE_ID,)

    async with session_factory() as session:
        world = ConversionWorld(session, storage, clock)
        head = await world.vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        assert head is not None
        head_id = head.id
        container = world.codec.parse(content=await world.store.load(actor=actor, vault_file=head))
        assert container.assets_by_id == {_PICTURE_ID: _PICTURE}

        # A later batch keeps the first batch's picture and payload.
        await world.progress.batch_ready(
            worker_id=WORKER,
            job_id=queued.job_id,
            update=_picture_batch(lineage_id, q2="Fråga två", q3=None),
            notes=(),
        )
        reopened = await world.open(actor, lineage_id)
        assert reopened.revision == 2
        assert reopened.items[0].body_asset_ids() == (_PICTURE_ID,)

        # A teacher save keeps the picture and its payload in the same exam file.
        saved = await world.teacher_save(actor, reopened)
        assert saved.summary.version == 3
        assert saved.summary.vault_file_id == head_id
        assert saved.document.items[0].body_asset_ids() == (_PICTURE_ID,)
        head = await world.vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        assert head is not None and head.id == head_id
        container = world.codec.parse(content=await world.store.load(actor=actor, vault_file=head))
        assert container.assets_by_id == {_PICTURE_ID: _PICTURE}
