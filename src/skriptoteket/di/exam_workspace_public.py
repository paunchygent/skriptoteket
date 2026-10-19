"""DI bindings for the public stateless exam workspace surface (ST-SKRIPT-41-02).

A focused provider for the routes guests reach without login: the course
catalog and misspellings JSON helpers, the shared QTI/PDF/DOCX renderer the
guest routes reuse exactly, and the stateless guest export/command handlers.
Signed-in conversion, document and export registrations stay in
``di.exam_workspace``.
"""

from __future__ import annotations

import random

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.handlers.exam_workspace_courses import (
    GetExamCourseCatalogHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_misspellings import (
    GenerateExamWorkspaceMisspellingsHandler,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_commands import (
    PublicExamWorkspaceCommandHandler,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_exports import (
    PublicExamWorkspaceExportHandler,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.exam_workspace import (
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
    GetExamCourseCatalogHandlerProtocol,
)
from skriptoteket.protocols.identity import ProfileRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ExamWorkspacePublicProvider(Provider):
    """Provide the public stateless exam workspace helpers and renderer."""

    @provide(scope=Scope.REQUEST)
    def course_catalog(
        self, profiles: ProfileRepositoryProtocol, uow: UnitOfWorkProtocol
    ) -> GetExamCourseCatalogHandlerProtocol:
        return GetExamCourseCatalogHandler(profiles=profiles, uow=uow)

    @provide(scope=Scope.APP)
    def misspellings(self) -> GenerateExamWorkspaceMisspellingsHandlerProtocol:
        return GenerateExamWorkspaceMisspellingsHandler()

    @provide(scope=Scope.REQUEST)
    def export_renderer(self) -> ExamWorkspaceExportRenderer:
        """Provide the shared QTI/PDF/DOCX renderer and checklist builder."""
        return ExamWorkspaceExportRenderer(
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=WeasyPrintExamNetPdfRenderer(),
            docx_writer=ExamWorkspaceDocxWriter(),
        )

    @provide(scope=Scope.REQUEST)
    def public_export_handler(
        self,
        renderer: ExamWorkspaceExportRenderer,
    ) -> PublicExamWorkspaceExportHandler:
        """Provide the stateless guest export handler."""
        return PublicExamWorkspaceExportHandler(renderer=renderer)

    @provide(scope=Scope.REQUEST)
    def public_command_handler(self) -> PublicExamWorkspaceCommandHandler:
        """Provide the stateless guest document command handler."""
        return PublicExamWorkspaceCommandHandler(rng=random.SystemRandom())
