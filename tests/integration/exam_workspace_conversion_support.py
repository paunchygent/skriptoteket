"""Shared production composition and provisional batches for progressive DOCX conversion proofs.

The job queue, vault repositories, container codec, local vault storage and the save/import
handlers are the production implementations; each test's provisional documents stand in for
the pipeline's batches.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentResponse,
)
from skriptoteket.application.curated_apps.exam_workspace_history import (
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_progress import (
    ExamWorkspaceConversionProgress,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceConversionStatusHandler,
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_edit_lease import (
    ExamWorkspaceEditLeaseHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_enrichment_jobs import (
    PostgreSQLExamAnswerKeyEnrichmentJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_index_repository import (
    PostgreSQLExamIndexRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from tests.fixtures.payload_guard_fixtures import unpooled_payload_guard_engine
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    choice,
    conversion_update,
    placeholder,
)

WORKER = "conversion-worker"
SETTINGS = Settings.model_construct(
    VAULT_MAX_FILE_BYTES=5_000_000, VAULT_MAX_TOTAL_BYTES=50_000_000
)


class Ids:
    """Fresh UUIDs for saved versions, so tests can assert on persisted rows."""

    def new_uuid(self) -> UUID:
        return uuid4()


class ConversionWorld:
    """The production conversion stack over one database session and vault root."""

    def __init__(
        self, session: AsyncSession, storage: LocalVaultStorage, clock: FixedClock
    ) -> None:
        self.clock = clock
        self.edit_tabs: dict[tuple[UUID, UUID], UUID] = {}
        self.uow = SQLAlchemyUnitOfWork(session)
        self.jobs = PostgreSQLExamAnswerKeyEnrichmentJobRepository(session)
        self.vault_files = PostgreSQLUserVaultFileRepository(
            session, unpooled_payload_guard_engine(session.bind)
        )
        self.codec = ExamWorkspaceContainerCodec()
        self.index = PostgreSQLExamIndexRepository(session)
        self.store = ExamWorkspaceDocumentStore(
            vault_files=self.vault_files,
            vault_usage=PostgreSQLUserVaultUsageRepository(session),
            vault_storage=storage,
            index=self.index,
            codec=self.codec,
            uow=self.uow,
            clock=clock,
            settings=SETTINGS,
        )
        self.progress = ExamWorkspaceConversionProgress(
            jobs=self.jobs,
            users=PostgreSQLUserRepository(session),
            vault_files=self.vault_files,
            store=self.store,
            codec=self.codec,
            uow=self.uow,
            clock=clock,
            id_generator=Ids(),
        )
        self.status = GetExamWorkspaceConversionStatusHandler(
            jobs=self.jobs, index=PostgreSQLExamIndexRepository(session)
        )

    async def opened(self, actor: User, lineage_id: UUID) -> ExamWorkspaceDocumentResponse:
        return await GetExamWorkspaceDocumentHandler(
            vault_files=self.vault_files,
            codec=self.codec,
            store=self.store,
            jobs=self.jobs,
            uow=self.uow,
        ).handle(actor=actor, lineage_id=lineage_id)

    async def open(self, actor: User, lineage_id: UUID) -> NativeExamDocument:
        return (await self.opened(actor, lineage_id)).document

    async def teacher_save(
        self, actor: User, document: NativeExamDocument
    ) -> ExamWorkspaceDocumentResponse:
        history = await self.store.get_history(actor=actor, lineage_id=document.document_id)
        await StoreExamWorkspaceUndoStepHandler(
            vault_files=self.vault_files,
            codec=self.codec,
            store=self.store,
            jobs=self.jobs,
            id_generator=Ids(),
            clock=self.clock,
        ).handle(
            actor=actor,
            lineage_id=document.document_id,
            request=StoreExamWorkspaceUndoStepRequest(
                expected_cursor=history.cursor,
                document=document,
                tab_id=await lease_tab(self, actor, document.document_id),
            ),
        )
        return await self.opened(actor, document.document_id)


async def lease_tab(world: ConversionWorld, actor: User, lineage: UUID) -> UUID:
    """Claim the edit lease for one tab per exam, like the editor's heartbeat."""
    key = (actor.id, lineage)
    tab = world.edit_tabs.get(key)
    if tab is None:
        tab = uuid4()
        await ExamWorkspaceEditLeaseHandler(
            vault_files=world.vault_files, store=world.store, clock=world.clock
        ).claim(actor=actor, lineage_id=lineage, tab_id=tab)
        world.edit_tabs[key] = tab
    return tab


def batch(lineage_id: UUID, *, q2: str | None, q3: str | None) -> ConversionUpdate:
    """Three questions; q2 and q3 stay placeholders while their converted text is None."""
    return conversion_update(
        [
            ("q1", [choice("p1", "Fråga ett")]),
            ("q2", [choice("p2", q2)] if q2 else [placeholder("p2", "Källtext två")]),
            ("q3", [choice("p3", q3)] if q3 else [placeholder("p3", "Källtext tre")]),
        ],
        pending=tuple(q for q, done in (("q2", q2), ("q3", q3)) if not done),
        document_id=lineage_id,
    )
