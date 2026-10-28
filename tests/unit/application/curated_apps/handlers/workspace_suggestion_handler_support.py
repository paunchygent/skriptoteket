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
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    FindExamWorkspaceAnswerKeySuggestionsHandler,
    GetExamWorkspaceAnswerKeySuggestionsStatusHandler,
    RequestExamWorkspaceAnswerKeySuggestionsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
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
    NativeAnswerKeyRetry,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
    InMemoryEnrichmentJobRepository,
    UUIDGenerator,
)
from tests.unit.application.curated_apps.handlers.enrichment_routing_test_support import (
    make_actor,
)
from tests.unit.application.curated_apps.handlers.exam_index_test_support import (
    InMemoryExamIndexRepository,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)
from tests.unit.application.curated_apps.handlers.vault_file_repository_test_support import (
    InMemoryVaultFileRepository,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body

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
    retry: NativeAnswerKeyRetry = NativeAnswerKeyRetry.NONE,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(
            NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=stem, marks=()),)),
        ),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("vägen")),
            NativeChoice(choice_id="choice_002", body=plain_body("eleverna")),
        ),
        answer_key=NativeAnswerKey(
            origin=origin,
            correct_choice_ids=("choice_001",)
            if origin is not NativeAnswerKeyOrigin.ABSENT
            else (),
        ),
        answer_key_retry=retry,
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
        self.vault_storage = InMemoryVaultStorage()
        self.codec = ExamWorkspaceContainerCodec()
        self.lineage_id = uuid4()
        head_id = uuid4()
        self.head_id = head_id
        now = NOW
        self.vault_files.files[head_id] = VaultFile(
            id=head_id,
            user_id=self.actor.id,
            name="prov.provdokument.zip",
            bytes=1,
            source_kind=VaultFileSourceKind.APP_EXPORT,
            document_lineage_id=self.lineage_id,
            document_version=3,
            created_at=now,
        )
        self.store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=InMemoryVaultUsageRepository(
                usage=VaultUsage(user_id=self.actor.id, bytes_total=0, updated_at=now)
            ),
            vault_storage=self.vault_storage,
            uow=FakeUow(),
            clock=FixedClock(now),
            settings=Settings.model_construct(
                VAULT_MAX_FILE_BYTES=5_000_000,
                VAULT_MAX_TOTAL_BYTES=50_000_000,
            ),
            index=InMemoryExamIndexRepository(self.vault_files),
            codec=self.codec,
        )
        self.seed_saved_head(suggestion_item(item_id="item_001", sequence=1))
        self.suggestion_jobs = InMemorySuggestionJobQueries(self.jobs)
        self.request_handler = RequestExamWorkspaceAnswerKeySuggestionsHandler(
            enrichment_jobs=self.jobs,
            suggestion_jobs=self.suggestion_jobs,
            enrichment_enabled=enabled,
            vault_files=self.vault_files,
            store=self.store,
            codec=self.codec,
            uow=FakeUow(),
            clock=FixedClock(now),
            id_generator=UUIDGenerator(),
        )
        self.status_handler = GetExamWorkspaceAnswerKeySuggestionsStatusHandler(
            enrichment_jobs=self.jobs,
        )
        self.find_handler = FindExamWorkspaceAnswerKeySuggestionsHandler(
            suggestion_jobs=self.suggestion_jobs,
            vault_files=self.vault_files,
        )

    def seed_saved_head(self, *items: NativeExamItem, revision: int = 3) -> None:
        """Write the saved head document these items build, at the head's version."""
        document = suggestion_document(self.lineage_id, *items).model_copy(
            update={"revision": revision}
        )
        self.vault_storage.stored[(self.actor.id, self.head_id)] = self.codec.build(
            content=ExamWorkspaceContainerContent(document=document, notes=(), assets_by_id={})
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
