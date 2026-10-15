"""Real Postgres proof for the workspace suggestion job lookups (TASK-SKRIPT-39-04-09).

Purpose:
    Prove one saved version may carry several suggestion jobs, the resume
    lookup reads the newest of them for the owner, exam and saved version
    only, and the reuse lookup matches a queued or running job by its exact
    sent content through JSONB equality (key order ignored).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

_NOW = datetime(2026, 10, 13, 12, tzinfo=UTC)
_VIEWS: dict[str, JsonValue] = {"views": [{"item_id": "item_001", "stem_text": "Vad?"}]}


def _job(
    *,
    owner_id: UUID,
    lineage_id: UUID,
    revision: int = 3,
    request: dict[str, JsonValue] = _VIEWS,
    created: datetime = _NOW,
) -> ExamAnswerKeyEnrichmentJob:
    return enqueue_workspace_enrichment_job(
        job_id=uuid4(),
        owner_user_id=owner_id,
        input_filename="Prov",
        workspace_lineage_id=lineage_id,
        workspace_document_revision=revision,
        workspace_request_json=request,
        now=created,
    )


async def test_one_saved_version_carries_several_jobs_and_the_newest_is_found(
    db_session: AsyncSession,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    owner, lineage = uuid4(), uuid4()
    older = _job(owner_id=owner, lineage_id=lineage)
    newer = _job(owner_id=owner, lineage_id=lineage, created=_NOW + timedelta(seconds=1))
    newest_other_version = _job(
        owner_id=owner, lineage_id=lineage, revision=4, created=_NOW + timedelta(seconds=2)
    )
    for job in (older, newer, newest_other_version):
        await jobs.create(job=job)

    found = await jobs.get_latest_workspace_job(
        owner_user_id=owner, workspace_lineage_id=lineage, workspace_document_revision=3
    )

    assert found is not None and found.id == newer.id
    assert found.workspace_document_revision == 3


async def test_latest_lookup_is_scoped_to_owner_exam_and_workspace_lane(
    db_session: AsyncSession,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    owner, lineage = uuid4(), uuid4()
    await jobs.create(job=_job(owner_id=uuid4(), lineage_id=lineage))
    await jobs.create(job=_job(owner_id=owner, lineage_id=uuid4()))
    await jobs.create(
        job=ExamAnswerKeyEnrichmentJob(
            id=uuid4(),
            source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
            owner_user_id=owner,
            status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
            input_filename="quiz.docx",
            source_docx=b"PK\x03\x04docx",
            workspace_lineage_id=lineage,
            workspace_document_revision=1,
            available_at=_NOW,
            created_at=_NOW,
            updated_at=_NOW,
        )
    )

    for revision in (1, 3):
        assert (
            await jobs.get_latest_workspace_job(
                owner_user_id=owner,
                workspace_lineage_id=lineage,
                workspace_document_revision=revision,
            )
            is None
        )


@pytest.mark.parametrize(
    ("status", "found"),
    [
        (ExamAnswerKeyEnrichmentJobStatus.QUEUED, True),
        (ExamAnswerKeyEnrichmentJobStatus.RUNNING, True),
        (ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED, False),
        (ExamAnswerKeyEnrichmentJobStatus.FAILED, False),
    ],
)
async def test_active_lookup_matches_pending_jobs_on_exact_content(
    db_session: AsyncSession, status: ExamAnswerKeyEnrichmentJobStatus, found: bool
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    owner, lineage = uuid4(), uuid4()
    job = _job(owner_id=owner, lineage_id=lineage)
    await jobs.create(job=job)
    await jobs.update(job=job.model_copy(update={"status": status}))

    # The same content with its keys in another order is the same request.
    reordered: dict[str, JsonValue] = {"views": [{"stem_text": "Vad?", "item_id": "item_001"}]}
    match = await jobs.get_active_workspace_job(
        owner_user_id=owner,
        workspace_lineage_id=lineage,
        workspace_document_revision=3,
        workspace_request_json=reordered,
    )
    edited = await jobs.get_active_workspace_job(
        owner_user_id=owner,
        workspace_lineage_id=lineage,
        workspace_document_revision=3,
        workspace_request_json={"views": [{"item_id": "item_001", "stem_text": "Vem?"}]},
    )
    other_version = await jobs.get_active_workspace_job(
        owner_user_id=owner,
        workspace_lineage_id=lineage,
        workspace_document_revision=2,
        workspace_request_json=_VIEWS,
    )

    assert (match is not None and match.id == job.id) is found
    assert edited is None
    assert other_version is None
