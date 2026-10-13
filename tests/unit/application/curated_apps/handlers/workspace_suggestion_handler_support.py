"""Shared harness for exam workspace suggestion handler tests.

Purpose:
    Give the request, status and find handler tests (TASK-SKRIPT-39-04-07,
    TASK-SKRIPT-39-04-09) one choice-question builder, one document builder
    at saved revision 3, an in-memory double of
    `ExamWorkspaceSuggestionJobQueryProtocol` over the in-memory job ledger,
    and a harness wiring the three handlers to those fakes.

Relationships:
    - Used by `test_exam_workspace_enrichment` and
      `test_exam_workspace_enrichment_resume`.
    - Builds on the job ledger fake in `answer_key_enrichment_test_support`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    FindExamWorkspaceAnswerKeySuggestionsHandler,
    GetExamWorkspaceAnswerKeySuggestionsStatusHandler,
    RequestExamWorkspaceAnswerKeySuggestionsHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
    InMemoryEnrichmentJobRepository,
    UUIDGenerator,
)
from tests.unit.application.curated_apps.handlers.enrichment_routing_test_support import (
    make_actor,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
)

_ACTIVE = (ExamAnswerKeyEnrichmentJobStatus.QUEUED, ExamAnswerKeyEnrichmentJobStatus.RUNNING)


class InMemorySuggestionJobQueries:
    """A double satisfying `ExamWorkspaceSuggestionJobQueryProtocol`."""

    def __init__(self, ledger: InMemoryEnrichmentJobRepository) -> None:
        self._ledger = ledger

    def _on_version(
        self, owner_user_id: UUID, workspace_lineage_id: UUID, workspace_document_revision: int
    ) -> list[ExamAnswerKeyEnrichmentJob]:
        return [
            job
            for job in self._ledger.jobs.values()
            if job.source_kind is ExamAnswerKeySourceKind.WORKSPACE
            and job.owner_user_id == owner_user_id
            and job.workspace_lineage_id == workspace_lineage_id
            and job.workspace_document_revision == workspace_document_revision
        ]

    async def get_latest_workspace_job(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
    ) -> ExamAnswerKeyEnrichmentJob | None:
        jobs = self._on_version(owner_user_id, workspace_lineage_id, workspace_document_revision)
        return max(jobs, key=lambda job: (job.created_at, job.id), default=None)

    async def get_active_workspace_job(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
        workspace_request_json: dict[str, JsonValue],
    ) -> ExamAnswerKeyEnrichmentJob | None:
        for job in self._on_version(
            owner_user_id, workspace_lineage_id, workspace_document_revision
        ):
            if job.status in _ACTIVE and job.workspace_request_json == workspace_request_json:
                return job
        return None

    async def lock_workspace_requests(
        self,
        *,
        owner_user_id: UUID,
        workspace_lineage_id: UUID,
        workspace_document_revision: int,
    ) -> None:
        # One event loop and no await inside the fake calls: nothing interleaves.
        return None


NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


def suggestion_item(
    *,
    item_id: str,
    sequence: int,
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.ABSENT,
    stem: str = "Vilket är huvudordet?",
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(NativeParagraph(segments=(NativeTextSegment(text=stem),)),),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", text="vägen"),
            NativeChoice(choice_id="choice_002", text="eleverna"),
        ),
        answer_key=NativeAnswerKey(
            origin=origin,
            correct_choice_ids=("choice_001",)
            if origin is not NativeAnswerKeyOrigin.ABSENT
            else (),
        ),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.TEACHER_CREATED,
        ),
    )


def suggestion_document(document_id: UUID, *items: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=document_id,
        revision=3,
        title="Omprov: grammatik",
        items=items,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


class SuggestionHandlerHarness:
    """Request, status and find handlers on in-memory jobs and one saved head at revision 3."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.actor = make_actor()
        self.jobs = InMemoryEnrichmentJobRepository()
        self.vault_files = InMemoryVaultFileRepository()
        self.lineage_id = uuid4()
        head_id = uuid4()
        self.vault_files.files[head_id] = VaultFile(
            id=head_id,
            user_id=self.actor.id,
            name="prov.provdokument.zip",
            bytes=1,
            source_kind=VaultFileSourceKind.APP_EXPORT,
            document_lineage_id=self.lineage_id,
            document_version=3,
            created_at=NOW,
        )
        self.suggestion_jobs = InMemorySuggestionJobQueries(self.jobs)
        self.request_handler = RequestExamWorkspaceAnswerKeySuggestionsHandler(
            enrichment_jobs=self.jobs,
            suggestion_jobs=self.suggestion_jobs,
            enrichment_enabled=enabled,
            vault_files=self.vault_files,
            uow=FakeUow(),
            clock=FixedClock(NOW),
            id_generator=UUIDGenerator(),
        )
        self.status_handler = GetExamWorkspaceAnswerKeySuggestionsStatusHandler(
            enrichment_jobs=self.jobs,
        )
        self.find_handler = FindExamWorkspaceAnswerKeySuggestionsHandler(
            suggestion_jobs=self.suggestion_jobs,
            vault_files=self.vault_files,
        )

    async def request(
        self, document: NativeExamDocument, item_id: str | None = None
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        return await self.request_handler.handle(
            actor=self.actor,
            lineage_id=self.lineage_id,
            request=RequestExamWorkspaceAnswerKeySuggestionsRequest(
                document=document, item_id=item_id
            ),
        )
