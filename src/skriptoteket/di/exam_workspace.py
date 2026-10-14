"""DI bindings for the native exam workspace (ST-SKRIPT-39-04).

A focused provider: the DOCX chunker and container codec are stateless
app-scoped adapters; the document store and handlers are request-scoped so
they share the request session, UoW, and vault repositories.
"""

from __future__ import annotations

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.handlers.exam_workspace_assets import (
    GetExamWorkspaceAssetHandler,
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
    ImportExamWorkspaceDocumentHandler,
    ListExamWorkspaceDocumentsHandler,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    DocxBuildRoundExchange,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline import (
    DocxConversionPipeline,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_retry import (
    RetryExamWorkspaceItemHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
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
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.llm.openai.docx_conversion_profiles import (
    build_luna_docx_conversion_profile,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.docx_conversion_progress import DocxConversionProgressProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyTokenLeaseRepositoryProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
)
from skriptoteket.protocols.exam_workspace import (
    DocxExamChunkerProtocol,
    ExamWorkspaceContainerCodecProtocol,
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamWorkspaceAssetHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    ListExamWorkspaceDocumentsHandlerProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class ExamWorkspaceProvider(Provider):
    """Provide exam workspace conversion, persistence, and handlers."""

    @provide(scope=Scope.APP)
    def docx_chunker(self) -> DocxExamChunkerProtocol:
        """Provide ordered source segmentation without item interpretation."""
        return PythonDocxExamChunker()

    @provide(scope=Scope.REQUEST)
    def docx_pipeline(
        self,
        client: httpx.AsyncClient,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        sleeper: SleeperProtocol,
        progress: DocxConversionProgressProtocol,
    ) -> DocxConversionPipeline:
        """Concurrent tasks share the request UoW one transaction at a time."""
        return build_docx_conversion_pipeline(
            client=client,
            provider=OpenAIAnswerKeyStructuredProvider(
                client=client,
                base_url=settings.LLM_ANSWER_KEY_BASE_URL,
                api_key=settings.OPENAI_LLM_ANSWER_KEY_API_KEY,
                timeout_seconds=float(settings.LLM_DOCX_CONVERSION_TIMEOUT_SECONDS),
            ),
            sleeper=sleeper,
            leases=leases,
            uow=SerializedUnitOfWork(uow),
            clock=clock,
            settings=settings,
            progress=progress,
        )

    @provide(scope=Scope.REQUEST)
    def process_docx_job(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        chunker: DocxExamChunkerProtocol,
        pipeline: DocxConversionPipeline,
        progress: DocxConversionProgressProtocol,
        store: ExamWorkspaceDocumentStore,
        users: UserRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ProcessExamWorkspaceDocxJobHandler:
        return ProcessExamWorkspaceDocxJobHandler(
            jobs=jobs,
            chunker=chunker,
            pipeline=pipeline,
            progress=progress,
            store=store,
            users=users,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def conversion_progress(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        users: UserRepositoryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        store: ExamWorkspaceDocumentStore,
        codec: ExamWorkspaceContainerCodecProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> DocxConversionProgressProtocol:
        """Provide progressive delivery of converted batches into the saved document."""
        return ExamWorkspaceConversionProgress(
            jobs=jobs,
            users=users,
            vault_files=vault_files,
            store=store,
            codec=codec,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def conversion_status_handler(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> GetExamWorkspaceConversionStatusHandlerProtocol:
        return GetExamWorkspaceConversionStatusHandler(jobs=jobs)

    @provide(scope=Scope.REQUEST)
    def retry_item_handler(
        self,
        client: httpx.AsyncClient,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
    ) -> RetryExamWorkspaceItemHandlerProtocol:
        """Provide the one-question retry handler; its one converter call rides the exchange."""
        return RetryExamWorkspaceItemHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            exchange=DocxBuildRoundExchange(
                provider=OpenAIAnswerKeyStructuredProvider(
                    client=client,
                    base_url=settings.LLM_ANSWER_KEY_BASE_URL,
                    api_key=settings.OPENAI_LLM_ANSWER_KEY_API_KEY,
                    timeout_seconds=float(settings.LLM_DOCX_CONVERSION_TIMEOUT_SECONDS),
                ),
                leases=leases,
                uow=uow,
                clock=clock,
            ),
            profile=build_luna_docx_conversion_profile(settings),
            enabled=settings.LLM_ANSWER_KEY_ENABLED,
        )

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
    ) -> ExamWorkspaceDocumentStore:
        """Provide the versioned Mina filer document store."""
        return ExamWorkspaceDocumentStore(
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def import_handler(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        id_generator: IdGeneratorProtocol,
    ) -> ImportExamWorkspaceDocumentHandlerProtocol:
        """Provide the DOCX import handler."""
        return ImportExamWorkspaceDocumentHandler(
            jobs=jobs, uow=uow, clock=clock, settings=settings, id_generator=id_generator
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
    def asset_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> GetExamWorkspaceAssetHandlerProtocol:
        """Provide the head-revision picture reader for the editor."""
        return GetExamWorkspaceAssetHandler(vault_files=vault_files, codec=codec, store=store)

    @provide(scope=Scope.REQUEST)
    def list_handler(
        self, vault_files: VaultFileRepositoryProtocol
    ) -> ListExamWorkspaceDocumentsHandlerProtocol:
        """Provide the head-version document list handler."""
        return ListExamWorkspaceDocumentsHandler(vault_files=vault_files)

    @provide(scope=Scope.REQUEST)
    def export_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> ExportExamWorkspaceDocumentHandlerProtocol:
        """Provide the on-demand export handler (QTI/PDF/DOCX)."""
        return ExportExamWorkspaceDocumentHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=WeasyPrintExamNetPdfRenderer(),
            docx_writer=ExamWorkspaceDocxWriter(),
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
        """Provide the versioned save handler."""
        return SaveExamWorkspaceDocumentHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            id_generator=id_generator,
            jobs=jobs,
        )
