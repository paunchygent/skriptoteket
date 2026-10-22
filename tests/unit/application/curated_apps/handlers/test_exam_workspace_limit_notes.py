"""Per-limit teacher notes on the retry, content and answer-key paths (R3).

Purpose:
    Prove every teacher-facing limit message on the R3 paths comes from
    ``ai_limit_note``: the one-question retry 429 carries the user note for a
    user-share refusal and the app note for pool, USD ceiling and the
    overage-cap (recorded as pool); the content-suggestion response and the
    answer-key status response do the same from the failed job's ``ai_limit``.

Relationships:
    - Exercises ``RetryExamWorkspaceItemHandler`` over a refusal exchange,
      ``content_response``/``ProcessExamContentSuggestionsHandler`` and
      ``suggestions_response_for_job``.
    - The DOCX pipeline scenarios live in the
      ``test_exam_workspace_*_door_limits.py`` files; this file owns the
      content-note and retry-note cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_content_tagging import (
    ExamContentTagSuggester,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceEnrichmentState,
    RetryExamWorkspaceItemRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
    content_response,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxRoundReply,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_retry import (
    RetryExamWorkspaceItemHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeyRequestPayload,
    suggestions_response_for_job,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import answer_key_item_views
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    AiJobOverageCapReached,
    ai_limit_note,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.enrichment_routing_test_support import (
    make_actor,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    PROFILE as RETRY_PROFILE,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    Env as RetryEnv,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    document as make_document,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    item as make_item,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    source as make_source,
)
from tests.unit.application.curated_apps.handlers.workspace_enrichment_job_support import (
    NOW,
    unkeyed_choice_document,
)
from tests.unit.application.curated_apps.handlers.workspace_suggestion_handler_support import (
    suggestion_document,
    suggestion_item,
)

pytestmark = pytest.mark.unit


class _RefusalExchange:
    """Raise one door refusal from the retry's exchange path."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def exchange(
        self,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
    ) -> DocxRoundReply:
        raise self._error


async def _retry_error(error: Exception) -> DomainError:
    env = RetryEnv()
    lineage_id = uuid4()
    saved = make_document(
        lineage_id=lineage_id,
        items=(make_item("item_001", 1, anchor="body:0001", source=make_source()),),
    )
    await env.seed(saved)
    handler = RetryExamWorkspaceItemHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        exchange=_RefusalExchange(error),
        profile=RETRY_PROFILE,
        enabled=True,
    )
    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=env.actor,
            lineage_id=lineage_id,
            request=RetryExamWorkspaceItemRequest(
                document=saved, item_id="item_001", kind=NativeExamItemKind.FREE_TEXT
            ),
        )
    return exc_info.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "note_limit"),
    [
        (AiDailyLimit.USER_SHARE, AiDailyLimit.USER_SHARE),
        (AiDailyLimit.POOL, AiDailyLimit.POOL),
        (AiDailyLimit.USD_CEILING, AiDailyLimit.USD_CEILING),
    ],
)
async def test_retry_429_carries_the_matching_note(
    limit: AiDailyLimit, note_limit: AiDailyLimit
) -> None:
    error = await _retry_error(AiDailyLimitReached(limit=limit))

    assert error.code is ErrorCode.AI_DAILY_LIMIT_REACHED
    assert error.message == ai_limit_note(note_limit)
    assert error.details == {"limit": limit.value}


@pytest.mark.asyncio
async def test_retry_429_for_the_overage_cap_carries_the_app_note() -> None:
    error = await _retry_error(
        AiJobOverageCapReached(overage_usd_micros=1_100_000, cap_usd_micros=1_000_000)
    )

    assert error.code is ErrorCode.AI_DAILY_LIMIT_REACHED
    assert error.message == ai_limit_note(AiDailyLimit.POOL)
    assert error.details == {"limit": AiDailyLimit.POOL.value}


def _content_job(
    *, last_error: str | None, limit: AiDailyLimit | None
) -> ExamAnswerKeyEnrichmentJob:
    lineage_id = uuid4()
    return ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.CONTENT_TAGS,
        owner_user_id=uuid4(),
        status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
        input_filename="prov",
        workspace_lineage_id=lineage_id,
        workspace_document_revision=3,
        workspace_course_key="SVESVE02",
        last_error=last_error,
        ai_limit=limit,
        available_at=NOW,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.parametrize(
    "limit",
    [AiDailyLimit.USER_SHARE, AiDailyLimit.POOL, AiDailyLimit.USD_CEILING],
)
def test_content_response_uses_the_note_for_the_limit(limit: AiDailyLimit) -> None:
    response = content_response(_content_job(last_error="ai_daily_limit", limit=limit))

    assert response.ai_limit is limit
    assert response.message == ai_limit_note(limit)


def test_content_response_uses_the_app_note_for_the_overage_cap() -> None:
    response = content_response(_content_job(last_error="ai_overage_cap", limit=AiDailyLimit.POOL))

    assert response.message == ai_limit_note(AiDailyLimit.POOL)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limit",
    [AiDailyLimit.USER_SHARE, AiDailyLimit.POOL, AiDailyLimit.USD_CEILING],
)
async def test_content_worker_records_the_limit_for_the_note(limit: AiDailyLimit) -> None:
    actor = make_actor()
    lineage_id = uuid4()
    unsaved_course = suggestion_document(
        lineage_id, suggestion_item(item_id="item_001", sequence=1, stem="Sparad fråga")
    )
    saved = unsaved_course.model_copy(
        update={
            "header": unsaved_course.header.model_copy(
                update={"course": ExamCourseChoice(key="SVESVE02", name="Svenska 2")}
            ),
        }
    )
    job = ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.CONTENT_TAGS,
        owner_user_id=actor.id,
        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
        input_filename="prov",
        workspace_lineage_id=lineage_id,
        workspace_document_revision=saved.revision,
        workspace_course_key="SVESVE02",
        workspace_request_json=saved.model_dump(mode="json"),
        available_at=NOW,
        created_at=NOW,
        updated_at=NOW,
        locked_by="content-worker",
    )
    jobs = AsyncMock(spec=ExamAnswerKeyEnrichmentJobRepositoryProtocol)
    jobs.update.side_effect = lambda *, job, expected_worker_id: job
    classifier = Mock(spec=ExamContentTagSuggester)
    classifier.suggest = AsyncMock(side_effect=AiDailyLimitReached(limit=limit))
    users = UserRepositoryStub()
    users.user = actor
    uow = AsyncMock(spec=UnitOfWorkProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = NOW
    worker = ProcessExamContentSuggestionsHandler(
        classifier=classifier,
        jobs=jobs,
        users=users,
        uow=uow,
        clock=clock,
    )

    finished = await worker.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_daily_limit"
    assert finished.ai_limit is limit
    assert content_response(finished).message == ai_limit_note(limit)


def _failed_workspace_job(
    *, last_error: str, limit: AiDailyLimit | None
) -> ExamAnswerKeyEnrichmentJob:
    document = unkeyed_choice_document(document_id=uuid4())
    views = answer_key_item_views(document)
    job = enqueue_workspace_enrichment_job(
        job_id=uuid4(),
        owner_user_id=uuid4(),
        input_filename=document.title,
        workspace_lineage_id=document.document_id,
        workspace_document_revision=document.revision,
        workspace_request_json=WorkspaceAnswerKeyRequestPayload(views=views).model_dump(
            mode="json"
        ),
        now=NOW,
    )
    return job.model_copy(
        update={
            "status": ExamAnswerKeyEnrichmentJobStatus.FAILED,
            "last_error": last_error,
            "ai_limit": limit,
        }
    )


@pytest.mark.parametrize(
    "limit",
    [AiDailyLimit.USER_SHARE, AiDailyLimit.POOL, AiDailyLimit.USD_CEILING],
)
def test_answer_key_status_response_uses_the_note_for_the_limit(
    limit: AiDailyLimit,
) -> None:
    response = suggestions_response_for_job(
        _failed_workspace_job(last_error="ai_daily_limit", limit=limit),
        lineage_id=uuid4(),
    )

    assert response.state is ExamWorkspaceEnrichmentState.FAILED
    assert response.message == ai_limit_note(limit)


def test_answer_key_status_response_uses_the_app_note_for_the_overage_cap() -> None:
    response = suggestions_response_for_job(
        _failed_workspace_job(last_error="ai_overage_cap", limit=AiDailyLimit.POOL),
        lineage_id=uuid4(),
    )

    assert response.state is ExamWorkspaceEnrichmentState.FAILED
    assert response.message == ai_limit_note(AiDailyLimit.POOL)


def test_answer_key_status_response_keeps_the_generic_note_without_a_limit() -> None:
    response = suggestions_response_for_job(
        _failed_workspace_job(last_error="llm_output_invalid", limit=None),
        lineage_id=uuid4(),
    )

    assert response.state is ExamWorkspaceEnrichmentState.FAILED
    assert response.message == "Facitförslaget kunde inte tolkas. Komplettera facit manuellt."
