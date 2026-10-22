"""Type-correct doubles and Dishka provider for the exam-workspace AI-gate test.

Purpose:
    Hold the recording protocol doubles, the handler bundle and the Dishka
    provider that the HTTP-level exam-workspace paid-AI gate test installs in
    place of the production dependency graph, plus the builder that assembles
    them. Keeping them here leaves the test module to its route assertions.

Relationships:
    - Imported by `tests/unit/web/test_apps_exam_workspace_ai_gate_api.py`,
      which supplies the sample item and exercises the gated routes.
    - The doubles implement the real `skriptoteket.protocols.exam_workspace`
      and content-tag handler contracts, so `ExamWorkspaceAiGateProvider`
      satisfies the FastAPI/Dishka graph without casts.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    ExamWorkspaceConversionStatus,
    ExamWorkspaceEnrichmentState,
    ExamWorkspaceItemRetryResponse,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
    RetryExamWorkspaceItemRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_content_suggestions import (
    ContentSuggestionsResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    RequestExamContentSuggestionsHandlerProtocol,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
)


class RecordingDouble:
    """Base for protocol doubles that record each received `handle` call."""

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []


class ContentSuggestionsDouble(RecordingDouble, RequestExamContentSuggestionsHandlerProtocol):
    """Recording double for the content-suggestions protocol."""

    def __init__(self, *, result: ContentSuggestionsResponse) -> None:
        super().__init__()
        self._result = result

    async def handle(self, *, actor: User, lineage_id: UUID) -> ContentSuggestionsResponse:
        self.calls.append((actor, lineage_id))
        return self._result


class DocumentImportDouble(
    RecordingDouble,
    ImportExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
):
    """Recording double for both DOCX and DigiExam document-import protocols."""

    def __init__(self, *, result: ExamWorkspaceConversionStatus) -> None:
        super().__init__()
        self._result = result

    async def handle(
        self, *, actor: User, filename: str, content: bytes, course_key: str | None
    ) -> ExamWorkspaceConversionStatus:
        self.calls.append((actor, filename, content, course_key))
        return self._result


class RetryItemDouble(RecordingDouble, RetryExamWorkspaceItemHandlerProtocol):
    """Recording double for the single-question retry protocol."""

    def __init__(self, *, result: ExamWorkspaceItemRetryResponse) -> None:
        super().__init__()
        self._result = result

    async def handle(
        self, *, actor: User, lineage_id: UUID, request: RetryExamWorkspaceItemRequest
    ) -> ExamWorkspaceItemRetryResponse:
        self.calls.append((actor, lineage_id, request))
        return self._result


class AnswerKeySuggestionsDouble(
    RecordingDouble, RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol
):
    """Recording double for the answer-key suggestions protocol."""

    def __init__(self, *, result: ExamWorkspaceAnswerKeySuggestionsResponse) -> None:
        super().__init__()
        self._result = result

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: RequestExamWorkspaceAnswerKeySuggestionsRequest,
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        self.calls.append((actor, lineage_id, request))
        return self._result


@dataclass(frozen=True)
class HandlerDoubles:
    """The five route handlers the gated and DigiExam routes receive."""

    content_suggestions: ContentSuggestionsDouble
    docx_import: DocumentImportDouble
    digiexam_import: DocumentImportDouble
    retry_item: RetryItemDouble
    answer_key_suggestions: AnswerKeySuggestionsDouble


class ExamWorkspaceAiGateProvider(Provider):
    def __init__(
        self,
        *,
        registry: CuratedAppRegistryProtocol,
        handlers: HandlerDoubles,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._handlers = handlers

    @provide(scope=Scope.REQUEST)
    def registry(self) -> CuratedAppRegistryProtocol:
        return self._registry

    @provide(scope=Scope.REQUEST)
    def request_exam_content_suggestions_handler(
        self,
    ) -> RequestExamContentSuggestionsHandlerProtocol:
        return self._handlers.content_suggestions

    @provide(scope=Scope.REQUEST)
    def import_exam_workspace_document_handler(
        self,
    ) -> ImportExamWorkspaceDocumentHandlerProtocol:
        return self._handlers.docx_import

    @provide(scope=Scope.REQUEST)
    def import_exam_workspace_digiexam_document_handler(
        self,
    ) -> ImportExamWorkspaceDigiExamDocumentHandlerProtocol:
        return self._handlers.digiexam_import

    @provide(scope=Scope.REQUEST)
    def retry_exam_workspace_item_handler(self) -> RetryExamWorkspaceItemHandlerProtocol:
        return self._handlers.retry_item

    @provide(scope=Scope.REQUEST)
    def request_exam_workspace_answer_key_suggestions_handler(
        self,
    ) -> RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol:
        return self._handlers.answer_key_suggestions


def _conversion_status(lineage_id: UUID) -> ExamWorkspaceConversionStatus:
    return ExamWorkspaceConversionStatus(
        job_id=uuid4(),
        lineage_id=lineage_id,
        state="queued",
        error_message=None,
        document_revision=None,
        questions_total=0,
        questions_done=0,
        questions_received=0,
        phase=None,
        phase_started_at=None,
        units=(),
        summary=None,
    )


def build_handler_doubles(*, sample_item: NativeExamItem) -> HandlerDoubles:
    """Assemble the five recording doubles the gate provider serves."""

    lineage_id = uuid4()
    return HandlerDoubles(
        content_suggestions=ContentSuggestionsDouble(
            result=ContentSuggestionsResponse(
                job_id=uuid4(),
                lineage_id=lineage_id,
                document_revision=1,
                course_key="MATMAT01a",
                state=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
            )
        ),
        docx_import=DocumentImportDouble(result=_conversion_status(lineage_id)),
        digiexam_import=DocumentImportDouble(result=_conversion_status(lineage_id)),
        retry_item=RetryItemDouble(
            result=ExamWorkspaceItemRetryResponse(
                lineage_id=lineage_id,
                item=sample_item,
            )
        ),
        answer_key_suggestions=AnswerKeySuggestionsDouble(
            result=ExamWorkspaceAnswerKeySuggestionsResponse(
                job_id=uuid4(),
                lineage_id=lineage_id,
                state=ExamWorkspaceEnrichmentState.QUEUED,
            )
        ),
    )
