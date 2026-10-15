"""Real Postgres proof that conversion progress is written only by its own method."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import JsonValue
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

_NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)
_PROGRESS: dict[str, JsonValue] = {
    "phase": "type_batches",
    "completed": ["multiple_choice"],
    "pending": ["free_text", "matching"],
    "counts": {"items": 12, "labelled": 5},
}


def _job() -> ExamAnswerKeyEnrichmentJob:
    return ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        owner_user_id=uuid4(),
        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
        input_filename="quiz.docx",
        source_docx=b"PK\x03\x04temporary-docx-bytes",
        workspace_lineage_id=uuid4(),
        workspace_document_revision=1,
        available_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )


async def test_stored_progress_is_read_by_the_status_view_and_the_locking_read(
    db_session: AsyncSession,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    stored = await jobs.create(job=_job())
    assert stored.conversion_progress is None
    initial_view = await jobs.get_conversion_view(job_id=stored.id)
    assert initial_view is not None and initial_view.conversion_progress is None

    await jobs.set_conversion_progress(job_id=stored.id, progress=_PROGRESS)
    await db_session.commit()
    db_session.expunge_all()

    view = await jobs.get_conversion_view(job_id=stored.id)
    assert view is not None and view.conversion_progress == _PROGRESS
    locked = await jobs.get_by_id_for_update(job_id=stored.id)
    assert locked is not None and locked.conversion_progress == _PROGRESS


async def test_update_with_a_progress_less_job_keeps_the_stored_progress(
    db_session: AsyncSession,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    stored = await jobs.create(job=_job())
    await jobs.set_conversion_progress(job_id=stored.id, progress=_PROGRESS)
    await db_session.commit()
    db_session.expunge_all()

    read_with_progress = await jobs.get_by_id_for_update(job_id=stored.id)
    assert read_with_progress is not None
    assert read_with_progress.conversion_progress == _PROGRESS
    stale_snapshot = read_with_progress.model_copy(
        update={"conversion_progress": None, "last_error": "retry later"}
    )
    updated = await jobs.update(job=stale_snapshot)
    await db_session.commit()
    db_session.expunge_all()

    assert updated.last_error == "retry later"
    assert updated.conversion_progress == _PROGRESS
    view = await jobs.get_conversion_view(job_id=stored.id)
    assert view is not None and view.conversion_progress == _PROGRESS
    assert view.last_error == "retry later"


async def test_set_conversion_progress_replaces_the_stored_value_and_rejects_a_missing_job(
    db_session: AsyncSession,
) -> None:
    jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(db_session)
    stored = await jobs.create(job=_job())
    await jobs.set_conversion_progress(job_id=stored.id, progress=_PROGRESS)
    replacement: dict[str, JsonValue] = {"phase": "done"}
    await jobs.set_conversion_progress(job_id=stored.id, progress=replacement)
    await db_session.commit()
    db_session.expunge_all()

    view = await jobs.get_conversion_view(job_id=stored.id)
    assert view is not None and view.conversion_progress == replacement
    with pytest.raises(DomainError) as exc_info:
        await jobs.set_conversion_progress(job_id=uuid4(), progress=_PROGRESS)
    assert exc_info.value.code is ErrorCode.NOT_FOUND
