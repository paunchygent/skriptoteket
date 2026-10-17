"""DI bindings for the saved-exam index repository and preferred-order query."""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.handlers.exam_workspace_saved_index import (
    ListExamWorkspaceDocumentsHandler,
)
from skriptoteket.infrastructure.repositories.exam_index_repository import (
    PostgreSQLExamIndexRepository,
)
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import ListExamWorkspaceDocumentsHandlerProtocol
from skriptoteket.protocols.identity import ProfileRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ExamWorkspaceIndexProvider(Provider):
    """Provide the saved-exam query with the request's shared session and UoW."""

    @provide(scope=Scope.REQUEST)
    def exam_index(self, session: AsyncSession) -> ExamIndexRepositoryProtocol:
        return PostgreSQLExamIndexRepository(session)

    @provide(scope=Scope.REQUEST)
    def list_handler(
        self,
        index: ExamIndexRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> ListExamWorkspaceDocumentsHandlerProtocol:
        """Provide the joined saved-exam index list handler."""
        return ListExamWorkspaceDocumentsHandler(index=index, profiles=profiles, uow=uow)
