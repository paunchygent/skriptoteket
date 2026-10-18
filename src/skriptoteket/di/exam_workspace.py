"""DI bindings for the native exam workspace (ST-SKRIPT-39-04).

A focused provider: the DOCX chunker and container codec are stateless
app-scoped adapters; the document store and handlers are request-scoped so
they share the request session, UoW, and vault repositories.
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_courses import (
    GetExamCourseCatalogHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceConversionStatusHandler,
    GetExamWorkspaceDocumentHandler,
    ImportExamWorkspaceDigiExamDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_misspellings import (
    GenerateExamWorkspaceMisspellingsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_parents import (
    ExamWorkspaceParentsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_undo_steps import (
    StoreExamWorkspaceUndoStepHandler,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_exports import (
    PublicExamWorkspaceExportHandler,
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
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
    GetExamCourseCatalogHandlerProtocol,
    GetExamWorkspaceAssetHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import (
    StoreExamWorkspaceUndoStepHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_parents import ExamWorkspaceParentsHandlerProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import ProfileRepositoryProtocol, UserRepositoryProtocol
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
    ) -> RequestExamContentSuggestionsHandler:
        return RequestExamContentSuggestionsHandler(
            reader=reader, jobs=jobs, uow=uow, clock=clock, id_generator=id_generator
        )

    @provide(scope=Scope.REQUEST)
    def get_content_suggestions(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> GetExamContentSuggestionsHandler:
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

    @provide(scope=Scope.REQUEST)
    def course_catalog(
        self, profiles: ProfileRepositoryProtocol, uow: UnitOfWorkProtocol
    ) -> GetExamCourseCatalogHandlerProtocol:
        return GetExamCourseCatalogHandler(profiles=profiles, uow=uow)

    @provide(scope=Scope.APP)
    def misspellings(self) -> GenerateExamWorkspaceMisspellingsHandlerProtocol:
        return GenerateExamWorkspaceMisspellingsHandler()

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
    def process_digiexam_job(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        store: ExamWorkspaceDocumentStore,
        users: UserRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
    ) -> ProcessExamWorkspaceDigiExamJobHandler:
        return ProcessExamWorkspaceDigiExamJobHandler(
            jobs=jobs,
            store=store,
            users=users,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            codec=codec,
        )

    @provide(scope=Scope.REQUEST)
    def import_digiexam_handler(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        id_generator: IdGeneratorProtocol,
    ) -> ImportExamWorkspaceDigiExamDocumentHandlerProtocol:
        return ImportExamWorkspaceDigiExamDocumentHandler(
            jobs=jobs,
            uow=uow,
            clock=clock,
            settings=settings,
            id_generator=id_generator,
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
    def export_renderer(self) -> ExamWorkspaceExportRenderer:
        """Provide the shared QTI/PDF/DOCX renderer and checklist builder."""
        return ExamWorkspaceExportRenderer(
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=WeasyPrintExamNetPdfRenderer(),
            docx_writer=ExamWorkspaceDocxWriter(),
        )

    @provide(scope=Scope.REQUEST)
    def export_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        renderer: ExamWorkspaceExportRenderer,
    ) -> ExportExamWorkspaceDocumentHandlerProtocol:
        """Provide the on-demand export handler (QTI/PDF/DOCX)."""
        return ExportExamWorkspaceDocumentHandler(
            vault_files=vault_files,
            codec=codec,
            store=store,
            renderer=renderer,
        )

    @provide(scope=Scope.REQUEST)
    def public_export_handler(
        self,
        renderer: ExamWorkspaceExportRenderer,
    ) -> PublicExamWorkspaceExportHandler:
        """Provide the stateless guest export handler."""
        return PublicExamWorkspaceExportHandler(renderer=renderer)

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
