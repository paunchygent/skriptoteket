"""Web contract for door limits (TASK-SKRIPT-41-01-03 B5).

Purpose:
    Prove every AI status shape exposes ``ai_limit`` and the synchronous
    one-question retry answers a door limit with HTTP 429, error code
    ``AI_DAILY_LIMIT_REACHED`` and ``details.limit`` naming the pool.

Relationships:
    - Exercises ``suggestions_response_for_job`` (enrichment), ``content_response``
      (content tags), ``conversion_status`` (documents), ``RetryExamWorkspaceItemHandler``
      (retry limit mapping), ``error_to_status`` and the central error boundary.
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    RetryExamWorkspaceItemRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_content_suggestions import (
    ContentSuggestionsResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    content_response,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    conversion_status,
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
from skriptoteket.protocols.exam_answer_key import StructuredLLMTextObserver
from skriptoteket.web.error_mapping import error_to_status
from skriptoteket.web.middleware.error_handler import error_handler_middleware
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    PROFILE as RETRY_PROFILE,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_retry_fixtures import (
    Env,
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

pytestmark = pytest.mark.unit


def _workspace_job(*, limit: AiDailyLimit | None) -> ExamAnswerKeyEnrichmentJob:
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
    if limit is None:
        return job
    return job.model_copy(update={"ai_limit": limit})


@pytest.mark.asyncio
async def test_answer_key_status_response_carries_ai_limit() -> None:
    response = suggestions_response_for_job(
        _workspace_job(limit=AiDailyLimit.USER_SHARE),
        lineage_id=uuid4(),
    )

    assert isinstance(response, ExamWorkspaceAnswerKeySuggestionsResponse)
    assert response.ai_limit is AiDailyLimit.USER_SHARE


@pytest.mark.asyncio
async def test_content_suggestions_status_response_carries_ai_limit() -> None:
    lineage_id = uuid4()
    job = ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.CONTENT_TAGS,
        owner_user_id=uuid4(),
        status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
        input_filename="prov",
        workspace_lineage_id=lineage_id,
        workspace_document_revision=1,
        workspace_course_key="MATMAT01a",
        available_at=NOW,
        created_at=NOW,
        updated_at=NOW,
        ai_limit=AiDailyLimit.POOL,
    )

    response = content_response(job)

    assert isinstance(response, ContentSuggestionsResponse)
    assert response.ai_limit is AiDailyLimit.POOL


@pytest.mark.asyncio
async def test_conversion_status_response_carries_ai_limit() -> None:
    view = ExamWorkspaceConversionJobView(
        id=uuid4(),
        owner_user_id=uuid4(),
        source_kind=ExamAnswerKeySourceKind.DOCX_IMPORT,
        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
        workspace_lineage_id=uuid4(),
        last_error=None,
        ai_limit=AiDailyLimit.USD_CEILING,
    )

    assert conversion_status(view).ai_limit is AiDailyLimit.USD_CEILING


def test_daily_limit_error_code_maps_to_429() -> None:
    assert error_to_status(ErrorCode.AI_DAILY_LIMIT_REACHED) == 429


class _LimitExchange:
    """Raise the door refusal the retry's exchange path propagates."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def exchange(
        self,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        caller: AiDoorCaller,
        *,
        on_text: StructuredLLMTextObserver | None = None,
    ) -> DocxRoundReply:
        raise self._error


async def _retry_with_exchange_error(error: Exception) -> DomainError:
    env = Env()
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
        exchange=_LimitExchange(error),
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
async def test_retry_maps_a_door_limit_to_the_limit_error() -> None:
    error = await _retry_with_exchange_error(AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE))

    assert error.code is ErrorCode.AI_DAILY_LIMIT_REACHED
    assert error.message == ai_limit_note(AiDailyLimit.USER_SHARE)
    assert error.details == {"limit": AiDailyLimit.USER_SHARE.value}


@pytest.mark.asyncio
async def test_retry_maps_an_overage_cap_refusal_to_the_pool_limit_error() -> None:
    error = await _retry_with_exchange_error(
        AiJobOverageCapReached(overage_usd_micros=1_100_000, cap_usd_micros=1_000_000)
    )

    assert error.code is ErrorCode.AI_DAILY_LIMIT_REACHED
    assert error.message == ai_limit_note(AiDailyLimit.POOL)
    assert error.details == {"limit": AiDailyLimit.POOL.value}


@pytest.mark.asyncio
async def test_retry_limit_error_reaches_http_as_429_with_details_limit() -> None:
    app = FastAPI()
    app.middleware("http")(error_handler_middleware)

    @app.post("/retry")
    async def retry() -> None:
        raise DomainError(
            code=ErrorCode.AI_DAILY_LIMIT_REACHED,
            message=ai_limit_note(AiDailyLimit.POOL),
            details={"limit": AiDailyLimit.POOL.value},
        )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/retry")

    assert response.status_code == 429
    payload = response.json()
    assert payload["error"]["code"] == "AI_DAILY_LIMIT_REACHED"
    assert payload["error"]["details"] == {"limit": "pool"}
