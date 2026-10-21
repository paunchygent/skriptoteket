"""Shared workspace-lane harness and provider doubles for enrichment job tests.

Purpose:
    Give the workspace-lane enrichment worker tests (TASK-SKRIPT-39-04-07) a
    fixed clock instant, unkeyed choice-question documents, a harness wiring the
    enrichment processor to in-memory fakes, and scripted structured
    providers that answer or fail one call at a time.

Relationships:
    - Shared by `test_exam_answer_key_enrichment_workspace_jobs` and
      `test_exam_answer_key_enrichment_workspace_partial_results`.
    - Builds on the protocol fakes in `answer_key_enrichment_test_support`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeySourceKind,
    enqueue_workspace_enrichment_job,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeyRequestPayload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_item_views,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
    InMemoryEnrichmentJobRepository,
    StubProvider,
    _route,
    docx_job_handler,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultStorage,
)
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body

NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


def unkeyed_choice_document(*, document_id: UUID) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=document_id,
        revision=7,
        title="Omprov utan facit",
        items=(
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.SINGLE_CHOICE,
                body=(
                    NativeParagraph(
                        heading_level=None,
                        segments=(
                            NativeTextSegment(text="Välj den grekiska bokstaven.", marks=()),
                        ),
                    ),
                ),
                points=2,
                choices=(
                    NativeChoice(choice_id="choice_001", body=plain_body("Alfa")),
                    NativeChoice(choice_id="choice_002", body=plain_body("Beta")),
                ),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
                review=NativeItemReview(
                    state=NativeItemReviewState.REVIEW_COMPLETE,
                    parse_origin=NativeParseOrigin.DETERMINISTIC,
                ),
            ),
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


class WorkspaceHarness:
    def __init__(self, *, provider: StubProvider, document: NativeExamDocument) -> None:
        self.owner_user_id = uuid4()
        self.enrichment_jobs = InMemoryEnrichmentJobRepository()
        self.provider = provider
        self.document = document

        vault_files = InMemoryVaultFileRepository()
        vault_storage = InMemoryVaultStorage()
        codec = ExamWorkspaceContainerCodec()
        self.handler = ProcessExamAnswerKeyEnrichmentJobHandler(
            enrichment_jobs=self.enrichment_jobs,
            provider=provider,
            provider_selector=FixedRouteAnswerKeyProviderSelector(route=_route()),
            uow=FakeUow(),
            clock=FixedClock(NOW),
            digiexam_handler=AsyncMock(spec=ProcessExamWorkspaceDigiExamJobHandler),
            content_tags_handler=AsyncMock(spec=ProcessExamContentSuggestionsHandler),
            docx_handler=docx_job_handler(
                enrichment_jobs=self.enrichment_jobs,
                provider=provider,
                vault_files=vault_files,
                vault_storage=vault_storage,
                codec=codec,
            ),
        )

    async def seed_claimed_job(self) -> ExamAnswerKeyEnrichmentJob:
        views = answer_key_item_views(self.document)
        await self.enrichment_jobs.create(
            job=enqueue_workspace_enrichment_job(
                job_id=uuid4(),
                owner_user_id=self.owner_user_id,
                input_filename=self.document.title,
                workspace_lineage_id=self.document.document_id,
                workspace_document_revision=self.document.revision,
                workspace_request_json=WorkspaceAnswerKeyRequestPayload(views=views).model_dump(
                    mode="json"
                ),
                now=NOW,
            )
        )
        claimed = await self.enrichment_jobs.claim_next(
            worker_id="worker-1",
            now=NOW,
            lease_ttl=timedelta(seconds=900),
        )
        assert claimed is not None
        assert claimed.source_kind is ExamAnswerKeySourceKind.WORKSPACE
        return claimed


class SequenceProvider(StubProvider):
    """Provider double answering each call with the next scripted content."""

    def __init__(self, contents: list[dict[str, JsonValue]]) -> None:
        super().__init__(content={}, usage=StructuredLLMUsage(total_tokens=50))
        self._contents = contents

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del request, profile
        self.call_count += 1
        return StructuredLLMResponse(
            content=self._contents[self.call_count - 1],
            finish_reason="completed",
            usage=StructuredLLMUsage(total_tokens=50),
        )


def three_unkeyed_choice_document(*, document_id: UUID) -> NativeExamDocument:
    document = unkeyed_choice_document(document_id=document_id)
    first = document.items[0]
    items = tuple(
        first.model_copy(update={"item_id": f"item_{index:03d}", "sequence": index})
        for index in (1, 2, 3)
    )
    return document.model_copy(update={"items": items})


class ScriptedProvider(StubProvider):
    """Provider double playing one scripted outcome (content or error) per call."""

    def __init__(self, outcomes: list[dict[str, JsonValue] | StructuredLLMProviderError]) -> None:
        super().__init__(content={}, usage=StructuredLLMUsage(total_tokens=50))
        self._outcomes = outcomes

    async def complete_structured(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        del request, profile
        self.call_count += 1
        outcome = self._outcomes[self.call_count - 1]
        if isinstance(outcome, StructuredLLMProviderError):
            raise outcome
        return StructuredLLMResponse(
            content=outcome,
            finish_reason="completed",
            usage=StructuredLLMUsage(total_tokens=50),
        )


def provider_error(code: StructuredLLMBackendFailureCode) -> StructuredLLMProviderError:
    return StructuredLLMProviderError(
        failure_code=code,
        message="provider failed",
        provider_id="fake",
    )
