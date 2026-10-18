"""DI bindings for the native exam workspace document editing (ST-SKRIPT-39-04).

A focused provider: the container codec is a stateless app-scoped adapter; the
document store and editing handlers are request-scoped so they share the
request session, UoW, and vault repositories. Conversion and import handlers
live in `exam_workspace_conversion.py`; the container resolves their shared
document-store and codec dependencies across the two providers.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.handlers.exam_workspace_assets import (
    GetExamWorkspaceAssetHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_parents import (
    ExamWorkspaceParentsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_print_preview import (
    PreviewExamWorkspacePrintHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_print_renderer import (
    WeasyPrintExamPrintRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
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
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceAssetHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    PreviewExamWorkspacePrintHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import (
    StoreExamWorkspaceUndoStepHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class ExamWorkspaceProvider(Provider):
    """Provide exam workspace document editing and export handlers."""

    @provide(scope=Scope.APP)
    def container_codec(self) -> ExamWorkspaceContainerCodecProtocol:
        """Provide the fail-closed container codec."""
        return ExamWorkspaceContainerCodec()

    @provide(scope=Scope.REQUEST)
    def document_store(
        self,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        index: ExamIndexRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
    ) -> ExamWorkspaceDocumentStore:
        """Provide the versioned Mina filer document store."""
        return ExamWorkspaceDocumentStore(
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            settings=settings,
            index=index,
            codec=codec,
        )

    @provide(scope=Scope.REQUEST)
    def get_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> GetExamWorkspaceDocumentHandlerProtocol:
        """Provide the reopen handler."""
        return GetExamWorkspaceDocumentHandler(
            vault_files=vault_files, codec=codec, store=store, jobs=jobs, uow=uow
        )

    @provide(scope=Scope.REQUEST)
    def parents_handler(
        self,
        reader: GetExamWorkspaceDocumentHandlerProtocol,
        undo_steps: StoreExamWorkspaceUndoStepHandlerProtocol,
    ) -> ExamWorkspaceParentsHandlerProtocol:
        return ExamWorkspaceParentsHandler(reader=reader, undo_steps=undo_steps)

    @provide(scope=Scope.REQUEST)
    def asset_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> GetExamWorkspaceAssetHandlerProtocol:
        """Provide the head-revision picture reader for the editor."""
        return GetExamWorkspaceAssetHandler(vault_files=vault_files, codec=codec, store=store)

    @provide(scope=Scope.REQUEST)
    def export_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> ExportExamWorkspaceDocumentHandlerProtocol:
        """Provide the on-demand export handler (QTI/print PDF/DOCX/Exam.net PDF)."""
        return ExportExamWorkspaceDocumentHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=WeasyPrintExamNetPdfRenderer(),
            docx_writer=ExamWorkspaceDocxWriter(),
            print_renderer=WeasyPrintExamPrintRenderer(),
        )

    @provide(scope=Scope.REQUEST)
    def print_preview_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> PreviewExamWorkspacePrintHandlerProtocol:
        """Provide the server-side student print preview (W5)."""
        return PreviewExamWorkspacePrintHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            print_renderer=WeasyPrintExamPrintRenderer(),
        )

    @provide(scope=Scope.REQUEST)
    def undo_step_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        id_generator: IdGeneratorProtocol,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> StoreExamWorkspaceUndoStepHandlerProtocol:
        return StoreExamWorkspaceUndoStepHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            id_generator=id_generator,
            jobs=jobs,
        )

    @provide(scope=Scope.REQUEST)
    def save_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        id_generator: IdGeneratorProtocol,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> SaveExamWorkspaceDocumentHandlerProtocol:
        """Provide the one-file save handler."""
        return SaveExamWorkspaceDocumentHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            id_generator=id_generator,
            jobs=jobs,
        )
