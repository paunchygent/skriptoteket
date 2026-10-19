"""DI bindings for the exam workspace sign-in guest-draft handoff (P5).

The handoff repository and its import handler are request-scoped so they share
the request session, UoW, document store, and container codec with the
signed-in exam workspace handlers.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_guest_draft_handoff import (
    ImportGuestExamDraftHandler,
)
from skriptoteket.infrastructure.repositories.exam_guest_draft_handoffs import (
    PostgreSQLExamGuestDraftHandoffRepository,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_guest_drafts import (
    ExamGuestDraftHandoffRepositoryProtocol,
    ImportGuestExamDraftHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol


class ExamWorkspaceGuestDraftsProvider(Provider):
    """Provide the guest-draft handoff ledger and its import handler."""

    @provide(scope=Scope.REQUEST)
    def guest_draft_handoff_repository(
        self, session: AsyncSession
    ) -> ExamGuestDraftHandoffRepositoryProtocol:
        return PostgreSQLExamGuestDraftHandoffRepository(session)

    @provide(scope=Scope.REQUEST)
    def import_guest_draft_handler(
        self,
        handoffs: ExamGuestDraftHandoffRepositoryProtocol,
        reader: GetExamWorkspaceDocumentHandlerProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        index: ExamIndexRepositoryProtocol,
    ) -> ImportGuestExamDraftHandlerProtocol:
        return ImportGuestExamDraftHandler(
            handoffs=handoffs,
            reader=reader,
            codec=codec,
            store=store,
            clock=clock,
            id_generator=id_generator,
            index=index,
        )
