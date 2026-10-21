"""DI bindings for the native exam workspace (ST-SKRIPT-39-04).

A focused provider: the DOCX chunker and container codec are stateless
app-scoped adapters; the document store and the remaining handlers are
request-scoped so they share the request session, UoW, and vault
repositories. Import lanes (DOCX, DigiExam, QTI) live in
``exam_workspace_imports``; the editing/export group also serves the
server-side student print preview. The public stateless surface (catalog,
misspellings, shared renderer, guest export and command handlers) lives in
``di.exam_workspace_public``.
"""

from __future__ import annotations

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.exam_content_tagging import (
    MeteredExamContentTagClassifier,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_assets import (
    GetExamWorkspaceAssetHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    GetExamContentSuggestionsHandler,
    ProcessExamContentSuggestionsHandler,
    RequestExamContentSuggestionsHandler,
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_edit_lease import (
    ExamWorkspaceEditLeaseHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
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
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_print_renderer import (
    WeasyPrintExamPrintRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_import_source import (  # noqa: E501
    ImportSourceChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
)
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
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
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    DocxExamChunkerProtocol,
    ExamWorkspaceContainerCodecProtocol,
    ExportExamWorkspaceDocumentHandlerProtocol,
    GetExamContentSuggestionsHandlerProtocol,
    GetExamWorkspaceAssetHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    PreviewExamWorkspacePrintHandlerProtocol,
    RequestExamContentSuggestionsHandlerProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import (
    ExamWorkspaceEditLeaseHandlerProtocol,
    StoreExamWorkspaceUndoStepHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
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

    @provide(scope=Scope.REQUEST)
    def content_classifier(
        self,
        client: httpx.AsyncClient,
        settings: Settings,
        sleeper: SleeperProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> MeteredExamContentTagClassifier:
        return MeteredExamContentTagClassifier(
            classifier=OpenAIDecisionsItemTypeLabeler(
                client=client,
                base_url=settings.LLM_ANSWER_KEY_BASE_URL,
                api_key=settings.OPENAI_LLM_ANSWER_KEY_API_KEY,
                timeout_seconds=float(settings.LLM_ITEM_LABELER_TIMEOUT_SECONDS),
                sleeper=sleeper,
                max_attempts=1,
            ),
            leases=leases,
            uow=uow,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def request_content_suggestions(
        self,
        reader: GetExamWorkspaceDocumentHandlerProtocol,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> RequestExamContentSuggestionsHandlerProtocol:
        return RequestExamContentSuggestionsHandler(
            reader=reader, jobs=jobs, uow=uow, clock=clock, id_generator=id_generator
        )

    @provide(scope=Scope.REQUEST)
    def get_content_suggestions(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> GetExamContentSuggestionsHandlerProtocol:
        return GetExamContentSuggestionsHandler(jobs=jobs)

    @provide(scope=Scope.REQUEST)
    def process_content_suggestions(
        self,
        classifier: MeteredExamContentTagClassifier,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> ProcessExamContentSuggestionsHandler:
        return ProcessExamContentSuggestionsHandler(
            classifier=classifier, jobs=jobs, uow=uow, clock=clock
        )

    @provide(scope=Scope.APP)
    def docx_chunker(self) -> DocxExamChunkerProtocol:
        """Provide ordered source segmentation of Word or PDF bytes without item interpretation."""
        return ImportSourceChunker(docx=PythonDocxExamChunker(), pdf=PdfPlumberExamChunker())

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
        index: ExamIndexRepositoryProtocol,
    ) -> GetExamWorkspaceConversionStatusHandlerProtocol:
        return GetExamWorkspaceConversionStatusHandler(jobs=jobs, index=index)

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
        renderer: ExamWorkspaceExportRenderer,
    ) -> ExportExamWorkspaceDocumentHandlerProtocol:
        """Provide the on-demand export handler (QTI/print PDF/DOCX/Exam.net PDF)."""
        return ExportExamWorkspaceDocumentHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            renderer=renderer,
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
        clock: ClockProtocol,
    ) -> StoreExamWorkspaceUndoStepHandlerProtocol:
        return StoreExamWorkspaceUndoStepHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            id_generator=id_generator,
            jobs=jobs,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def edit_lease_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        store: ExamWorkspaceDocumentStore,
        clock: ClockProtocol,
    ) -> ExamWorkspaceEditLeaseHandlerProtocol:
        """Provide one exam's edit lease: claim, heartbeat renew, takeover and release."""
        return ExamWorkspaceEditLeaseHandler(vault_files=vault_files, store=store, clock=clock)

    @provide(scope=Scope.REQUEST)
    def save_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        id_generator: IdGeneratorProtocol,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> SaveExamWorkspaceDocumentHandlerProtocol:
        """Provide the history-step reads and the copy-as-new-exam handler."""
        return SaveExamWorkspaceDocumentHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            id_generator=id_generator,
            jobs=jobs,
        )
