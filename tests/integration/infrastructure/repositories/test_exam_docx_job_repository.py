"""Real Postgres proof for DOCX bytes, lane isolation and completion fences."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    finish_enrichment_job,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

_NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
_TTL = timedelta(seconds=30)
_DOCX = b"PK\x03\x04temporary-docx-bytes"


def _job(
    *,
    lineage_id: UUID | None = None,
    owner_id: UUID | None = None,
    source_kind: ExamAnswerKeySourceKind = ExamAnswerKeySourceKind.DOCX_IMPORT,
    now: datetime = _NOW,
) -> ExamAnswerKeyEnrichmentJob:
    return ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=source_kind,
        owner_user_id=owner_id or uuid4(),
        status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
        input_filename="quiz.docx",
        source_docx=_DOCX if source_kind is ExamAnswerKeySourceKind.DOCX_IMPORT else None,
        workspace_lineage_id=lineage_id or uuid4(),
        workspace_document_revision=1,
        available_at=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize(
    "terminal_status",
    [ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, ExamAnswerKeyEnrichmentJobStatus.FAILED],
)
async def test_docx_bytes_survive_commit_and_are_deleted_at_terminal_state(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    terminal_status: ExamAnswerKeyEnrichmentJobStatus,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    queued = _job()
    stored = await jobs.create(job=queued)
    assert stored.source_docx == _DOCX
    await db_session.commit()

    async with session_factory() as reader:
        read_jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(reader)
        fetched = await read_jobs.get_by_id(job_id=queued.id)
        assert fetched is not None and fetched.source_docx == _DOCX
        claimed = await read_jobs.claim_next(worker_id="worker", now=_NOW, lease_ttl=_TTL)
        assert claimed is not None and claimed.source_docx == _DOCX
        terminal = claimed.model_copy(
            update={
                "status": terminal_status,
                "source_docx": None,
                "locked_by": None,
                "locked_until": None,
                "finished_at": _NOW,
            }
        )
        await read_jobs.update(job=terminal, expected_worker_id="worker")
        await reader.commit()

    async with session_factory() as reader:
        model = await reader.get(ExamAnswerKeyEnrichmentJobModel, queued.id)
        assert model is not None
        assert model.status == terminal_status.value
        assert model.source_docx is None


async def test_docx_failure_diagnostics_survive_commit_and_reload(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    queued = await jobs.create(job=_job())
    assert queued.diagnostics == ()
    diagnostics: tuple[dict[str, JsonValue], ...] = (
        {
            "stage": "admission",
            "code": "native_contract_invalid",
            "round": 1,
            "item": 0,
            "anchors": ["body:0006"],
            "detail": "x",
        },
    )
    finished = finish_enrichment_job(
        job=queued,
        status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
        now=_NOW,
        last_error="conversion failed",
        diagnostics=diagnostics,
    ).model_copy(update={"source_docx": None})
    await jobs.update(job=finished)
    await db_session.commit()

    async with session_factory() as reader:
        fetched = await PostgreSQLExamAnswerKeyEnrichmentJobRepository(reader).get_by_id(
            job_id=queued.id
        )
        assert fetched is not None
        assert fetched.diagnostics == diagnostics
        assert fetched.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
        assert fetched.source_docx is None
        assert (
            finish_enrichment_job(
                job=fetched, status=ExamAnswerKeyEnrichmentJobStatus.FAILED, now=_NOW
            ).diagnostics
            == diagnostics
        )
        assert (
            finish_enrichment_job(
                job=fetched,
                status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                now=_NOW,
                diagnostics=(),
            ).diagnostics
            == ()
        )


async def test_import_and_enrichment_coexist_at_revision_one_and_lookup_is_lane_specific(
    db_session: AsyncSession,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    imported = _job()
    await jobs.create(job=imported)
    assert imported.workspace_lineage_id is not None
    assert (
        await jobs.get_by_workspace_revision(
            owner_user_id=imported.owner_user_id,
            workspace_lineage_id=imported.workspace_lineage_id,
            workspace_document_revision=1,
        )
        is None
    )
    workspace = _job(
        lineage_id=imported.workspace_lineage_id,
        owner_id=imported.owner_user_id,
        source_kind=ExamAnswerKeySourceKind.WORKSPACE,
    )
    await jobs.create(job=workspace)
    fetched = await jobs.get_by_workspace_revision(
        owner_user_id=imported.owner_user_id,
        workspace_lineage_id=imported.workspace_lineage_id,
        workspace_document_revision=1,
    )
    assert fetched is not None and fetched.id == workspace.id
    assert fetched.source_kind is ExamAnswerKeySourceKind.WORKSPACE
    assert fetched.source_docx is None
    assert (
        await jobs.get_by_workspace_revision(
            owner_user_id=uuid4(),
            workspace_lineage_id=imported.workspace_lineage_id,
            workspace_document_revision=1,
        )
        is None
    )


@pytest.mark.parametrize(
    "source_kind", [ExamAnswerKeySourceKind.DOCX_IMPORT, ExamAnswerKeySourceKind.WORKSPACE]
)
async def test_each_lane_rejects_duplicate_binding(
    db_session: AsyncSession, source_kind: ExamAnswerKeySourceKind
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    first = _job(source_kind=source_kind)
    await jobs.create(job=first)
    duplicate = first.model_copy(update={"id": uuid4()})
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await jobs.create(job=duplicate)


async def test_docx_only_claim_leaves_workspace_queued_and_default_claim_preserves_order(
    db_session: AsyncSession,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    workspace = _job(source_kind=ExamAnswerKeySourceKind.WORKSPACE, now=_NOW - _TTL)
    imported = _job()
    await jobs.create(job=workspace)
    await jobs.create(job=imported)
    claimed = await jobs.claim_next(
        worker_id=" docx-worker ",
        now=_NOW,
        lease_ttl=_TTL,
        source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
    )
    assert claimed is not None and claimed.id == imported.id
    assert claimed.attempts == 1 and claimed.locked_by == "docx-worker"
    assert claimed.locked_until == _NOW + _TTL
    assert (
        await jobs.claim_next(
            worker_id="docx-worker",
            now=_NOW,
            lease_ttl=_TTL,
            source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        )
        is None
    )
    default_claim = await jobs.claim_next(worker_id="workspace-worker", now=_NOW, lease_ttl=_TTL)
    assert default_claim is not None and default_claim.id == workspace.id


async def test_docx_only_reap_leaves_workspace_expired_and_default_reap_still_claims_it(
    db_session: AsyncSession,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    workspace = _job(source_kind=ExamAnswerKeySourceKind.WORKSPACE, now=_NOW - _TTL)
    imported = _job()
    for queued in (workspace, imported):
        await jobs.create(
            job=queued.model_copy(
                update={
                    "status": ExamAnswerKeyEnrichmentJobStatus.RUNNING,
                    "attempts": 1,
                    "locked_by": "expired-worker",
                    "locked_until": _NOW - timedelta(seconds=1),
                }
            )
        )
    reaped = await jobs.claim_next_expired(
        worker_id="docx-reaper",
        now=_NOW,
        lease_ttl=_TTL,
        source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
    )
    assert reaped is not None and reaped.id == imported.id
    assert reaped.attempts == 1 and reaped.locked_by == "docx-reaper"
    assert reaped.source_docx == _DOCX
    default_reap = await jobs.claim_next_expired(worker_id="reaper", now=_NOW, lease_ttl=_TTL)
    assert default_reap is not None and default_reap.id == workspace.id


@pytest.mark.parametrize("expired", [False, True])
async def test_locked_row_is_skipped_by_another_claim_or_reaper(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    expired: bool,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    first = _job(now=_NOW - _TTL)
    second = _job()
    for queued in (first, second):
        if expired:
            queued = queued.model_copy(
                update={
                    "status": ExamAnswerKeyEnrichmentJobStatus.RUNNING,
                    "attempts": 1,
                    "locked_by": "old-worker",
                    "locked_until": _NOW - timedelta(seconds=1),
                }
            )
        await jobs.create(job=queued)
    await db_session.commit()
    locked = await jobs.get_by_id_for_update(job_id=first.id)
    assert locked is not None
    async with session_factory() as contender:
        competing_jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(contender)
        claim = competing_jobs.claim_next_expired if expired else competing_jobs.claim_next
        claimed = await claim(
            worker_id="contender",
            now=_NOW,
            lease_ttl=_TTL,
            source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        )
        assert claimed is not None and claimed.id == second.id
        assert await claim(worker_id="contender", now=_NOW, lease_ttl=_TTL) is None


async def test_completion_lock_refreshes_cached_ownership_and_fences_stale_worker(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    queued = _job()
    await jobs.create(job=queued)
    claimed = await jobs.claim_next(worker_id="old-worker", now=_NOW, lease_ttl=_TTL)
    assert claimed is not None
    cached_model = await db_session.get(ExamAnswerKeyEnrichmentJobModel, queued.id)
    assert cached_model is not None
    await db_session.commit()
    later = _NOW + _TTL + timedelta(seconds=1)
    async with session_factory() as reaper:
        reaped = await PostgreSQLExamAnswerKeyEnrichmentJobRepository(reaper).claim_next_expired(
            worker_id="new-worker", now=later, lease_ttl=_TTL
        )
        assert reaped is not None and reaped.id == queued.id
        await reaper.commit()
    assert cached_model.locked_by == "old-worker"
    live = await jobs.get_by_id_for_update(job_id=queued.id)
    assert live is not None and live.locked_by == "new-worker"
    assert cached_model.locked_by == "new-worker"
    terminal = claimed.model_copy(
        update={"status": ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, "source_docx": None}
    )
    with pytest.raises(DomainError) as exc_info:
        await jobs.update(job=terminal, expected_worker_id="old-worker")
    assert exc_info.value.code is ErrorCode.CONFLICT
    assert not await jobs.heartbeat(
        job_id=queued.id, worker_id="old-worker", now=later, lease_ttl=_TTL
    )
    assert await jobs.heartbeat(job_id=queued.id, worker_id="new-worker", now=later, lease_ttl=_TTL)
    retained = await jobs.get_by_id(job_id=queued.id)
    assert retained is not None and retained.source_docx == _DOCX
    assert retained.status is ExamAnswerKeyEnrichmentJobStatus.RUNNING
    assert await jobs.get_by_id_for_update(job_id=uuid4()) is None
