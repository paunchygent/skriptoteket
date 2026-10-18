"""DI bindings for the exam workspace sign-in guest-draft handoff (P5).

The handoff repository and its import handler are request-scoped so they share
the request session, UoW, document store, and vault repositories with the
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
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_guest_drafts import (
    ExamGuestDraftHandoffRepositoryProtocol,
    ImportGuestExamDraftHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


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
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ImportGuestExamDraftHandlerProtocol:
        return ImportGuestExamDraftHandler(
            handoffs=handoffs,
            reader=reader,
            vault_files=vault_files,
            codec=codec,
            store=store,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )
