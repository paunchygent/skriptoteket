"""Concurrent suggestion requests on real Postgres (TASK-SKRIPT-39-04-09 P3, repair 1 F1).

Purpose:
    Prove the request handler decides reuse-or-enqueue as one serialized step
    per owner, exam and saved version: two equal requests in two sessions get
    one job, two requests with different content get one job each.

Interleaving:
    Request 1 pauses right after its active-job lookup. Request 2 then runs
    for a while before request 1 continues. Without serialization request 2
    finds nothing and commits its own job before request 1 inserts a second
    one. With it, request 2 waits until request 1 has committed and then finds
    request 1's job. Pausing both requests after their lookups would deadlock
    a correct implementation, so only request 1 pauses.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    RequestExamWorkspaceAnswerKeySuggestionsHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.infrastructure.db.models.exam_answer_key_enrichment_job import (
    ExamAnswerKeyEnrichmentJobModel,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
    UUIDGenerator,
)
from tests.unit.application.curated_apps.handlers.workspace_suggestion_handler_support import (
    NOW,
    SuggestionHandlerHarness,
    suggestion_document,
    suggestion_item,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.docker,
    pytest.mark.asyncio(loop_scope="module"),
]

# Long enough for an unserialized request 2 to look up, insert and commit.
_SECOND_REQUEST_HEAD_START_S = 0.3


class _PausingAfterLookup(PostgreSQLExamAnswerKeyEnrichmentJobRepository):
    """Signals once its active-job lookup has returned, then waits to continue."""

    def __init__(
        self, session: AsyncSession, *, looked_up: asyncio.Event, resume: asyncio.Event
    ) -> None:
        super().__init__(session)
        self._looked_up = looked_up
        self._resume = resume

    async def get_active_workspace_job(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
        workspace_request_json: dict[str, JsonValue],
    ) -> ExamAnswerKeyEnrichmentJob | None:
        job = await super().get_active_workspace_job(
            owner_user_id=owner_user_id,
            workspace_lineage_id=workspace_lineage_id,
            workspace_document_revision=workspace_document_revision,
            workspace_request_json=workspace_request_json,
        )
        self._looked_up.set()
        await self._resume.wait()
        return job


async def _request(
    session: AsyncSession,
    repository: PostgreSQLExamAnswerKeyEnrichmentJobRepository,
    harness: SuggestionHandlerHarness,
    document: NativeExamDocument,
) -> ExamWorkspaceAnswerKeySuggestionsResponse:
    handler = RequestExamWorkspaceAnswerKeySuggestionsHandler(
        enrichment_jobs=repository,
        suggestion_jobs=repository,
        enrichment_enabled=True,
        vault_files=harness.vault_files,
        uow=SQLAlchemyUnitOfWork(session),
        clock=FixedClock(NOW),
        id_generator=UUIDGenerator(),
    )
    return await handler.handle(
        actor=harness.actor,
        lineage_id=harness.lineage_id,
        request=RequestExamWorkspaceAnswerKeySuggestionsRequest(document=document),
    )


async def _race(
    session_factory: async_sessionmaker[AsyncSession],
    harness: SuggestionHandlerHarness,
    first_document: NativeExamDocument,
    second_document: NativeExamDocument,
) -> tuple[ExamWorkspaceAnswerKeySuggestionsResponse, ExamWorkspaceAnswerKeySuggestionsResponse]:
    looked_up, resume = asyncio.Event(), asyncio.Event()

    async def first() -> ExamWorkspaceAnswerKeySuggestionsResponse:
        async with session_factory() as session:
            repository = _PausingAfterLookup(session, looked_up=looked_up, resume=resume)
            return await _request(session, repository, harness, first_document)

    async def second() -> ExamWorkspaceAnswerKeySuggestionsResponse:
        async with session_factory() as session:
            repository = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
            return await _request(session, repository, harness, second_document)

    first_task = asyncio.create_task(first())
    await looked_up.wait()
    second_task = asyncio.create_task(second())
    await asyncio.sleep(_SECOND_REQUEST_HEAD_START_S)
    resume.set()
    return await first_task, await second_task


async def _stored_jobs(session_factory: async_sessionmaker[AsyncSession], lineage_id: UUID) -> int:
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(ExamAnswerKeyEnrichmentJobModel)
            .where(ExamAnswerKeyEnrichmentJobModel.workspace_lineage_id == lineage_id)
        )
    return count or 0


async def test_equal_concurrent_requests_return_one_job(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    harness = SuggestionHandlerHarness()
    document = suggestion_document(
        harness.lineage_id, suggestion_item(item_id="item_001", sequence=1)
    )

    first, second = await _race(session_factory, harness, document, document)

    assert first.job_id is not None
    assert second.job_id == first.job_id
    assert await _stored_jobs(session_factory, harness.lineage_id) == 1


async def test_concurrent_requests_with_different_content_get_one_job_each(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    harness = SuggestionHandlerHarness()
    document = suggestion_document(
        harness.lineage_id, suggestion_item(item_id="item_001", sequence=1)
    )
    edited = suggestion_document(
        harness.lineage_id,
        suggestion_item(item_id="item_001", sequence=1, stem="Vilket är subjektet?"),
    )

    first, second = await _race(session_factory, harness, document, edited)

    assert first.job_id is not None and second.job_id is not None
    assert first.job_id != second.job_id
    assert await _stored_jobs(session_factory, harness.lineage_id) == 2
