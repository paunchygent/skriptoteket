"""Request-scoped wiring for the question-type command."""

import random

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.handlers.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandler,
)
from skriptoteket.protocols.exam_workspace import GetExamWorkspaceDocumentHandlerProtocol
from skriptoteket.protocols.exam_workspace_change_type import (
    ChangeExamWorkspaceItemTypeHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol


class ExamWorkspaceChangeTypeProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def change_type_handler(
        self,
        reader: GetExamWorkspaceDocumentHandlerProtocol,
        undo_steps: StoreExamWorkspaceUndoStepHandlerProtocol,
    ) -> ChangeExamWorkspaceItemTypeHandlerProtocol:
        return ChangeExamWorkspaceItemTypeHandler(
            reader=reader, undo_steps=undo_steps, rng=random.SystemRandom()
        )
