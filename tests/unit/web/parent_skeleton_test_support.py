"""Shared DI provider for the exam-workspace parent HTTP skeleton tests."""

from dishka import Provider, Scope, from_context

from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol


class SkeletonProvider(Provider):
    registry = from_context(provides=CuratedAppRegistryProtocol, scope=Scope.APP)
    reader = from_context(provides=GetExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    writer = from_context(provides=SaveExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
    parents = from_context(provides=ExamWorkspaceParentsHandlerProtocol, scope=Scope.APP)
    undo_steps = from_context(provides=StoreExamWorkspaceUndoStepHandlerProtocol, scope=Scope.APP)
    exporter = from_context(provides=ExportExamWorkspaceDocumentHandlerProtocol, scope=Scope.APP)
