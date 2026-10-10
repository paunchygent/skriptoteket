"""DI bindings for the Document Converter curated app.

Document rendering adapters, artifact and preview stores, producer policy, and
the converter job, saved-source, preview, and artifact handlers.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.document_converter_producers import (
    DocumentConverterProducerPolicy,
    LocalDocumentConverterProducer,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_document_converter import (
    DownloadDocumentConverterArtifactHandler,
    GetDocumentConverterJobHandler,
    SaveDocumentConverterArtifactHandler,
)
from skriptoteket.application.curated_apps.handlers.document_converter_jobs import (
    CreateDocumentConverterJobsHandler,
)
from skriptoteket.application.curated_apps.handlers.document_converter_project_previews import (
    CleanupDocumentConverterProjectPreviewsHandler,
    DiscardDocumentConverterProjectPreviewHandler,
    DownloadDocumentConverterProjectPreviewArtifactHandler,
    GetDocumentConverterProjectPreviewHandler,
    RenderDocumentConverterProjectPreviewHandler,
    SaveDocumentConverterProjectPreviewArtifactHandler,
)
from skriptoteket.application.curated_apps.handlers.document_converter_saved_sources import (
    ListDocumentConverterSavedFilesHandler,
    SubmitDocumentConverterSavedFileHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.documents.document_converter_artifacts import (
    FilesystemDocumentConverterArtifactStore,
)
from skriptoteket.infrastructure.documents.document_converter_project_preview_store import (
    FilesystemDocumentConverterProjectPreviewStore,
)
from skriptoteket.infrastructure.documents.document_converter_project_previews import (
    WeasyPrintDocumentConverterProjectRenderer,
)
from skriptoteket.infrastructure.documents.markdown_rendering import PythonMarkdownToHtmlRenderer
from skriptoteket.infrastructure.documents.pdf_rendering import WeasyPrintHtmlToPdfRenderer
from skriptoteket.infrastructure.documents.pdf_text_extraction import PdfPlumberTextExtractor
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol
from skriptoteket.protocols.document_converter import (
    DocumentConverterArtifactStoreProtocol,
    DocumentConverterProjectPreviewRendererProtocol,
    DocumentConverterProjectPreviewStoreProtocol,
    LocalDocumentConverterProducerProtocol,
)
from skriptoteket.protocols.documents import (
    HtmlToPdfRendererProtocol,
    MarkdownToHtmlRendererProtocol,
    PdfTextExtractorProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertALotClientV2Protocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class DocumentConverterProvider(Provider):
    """Provide Document Converter adapters and application handlers."""

    @provide(scope=Scope.APP)
    def document_html_to_pdf_renderer(self) -> HtmlToPdfRendererProtocol:
        return WeasyPrintHtmlToPdfRenderer()

    @provide(scope=Scope.APP)
    def document_markdown_to_html_renderer(self) -> MarkdownToHtmlRendererProtocol:
        return PythonMarkdownToHtmlRenderer()

    @provide(scope=Scope.APP)
    def document_pdf_text_extractor(self) -> PdfTextExtractorProtocol:
        return PdfPlumberTextExtractor()

    @provide(scope=Scope.APP)
    def document_converter_artifact_store(
        self,
        settings: Settings,
    ) -> DocumentConverterArtifactStoreProtocol:
        return FilesystemDocumentConverterArtifactStore(artifacts_root=settings.ARTIFACTS_ROOT)

    @provide(scope=Scope.APP)
    def document_converter_project_preview_renderer(
        self,
    ) -> DocumentConverterProjectPreviewRendererProtocol:
        return WeasyPrintDocumentConverterProjectRenderer()

    @provide(scope=Scope.APP)
    def document_converter_project_preview_store(
        self,
        settings: Settings,
    ) -> DocumentConverterProjectPreviewStoreProtocol:
        return FilesystemDocumentConverterProjectPreviewStore(
            artifacts_root=settings.ARTIFACTS_ROOT
        )

    @provide(scope=Scope.REQUEST)
    def document_converter_producer_policy(
        self,
        pdf_text_extractor: PdfTextExtractorProtocol,
    ) -> DocumentConverterProducerPolicy:
        return DocumentConverterProducerPolicy(pdf_text_extractor=pdf_text_extractor)

    @provide(scope=Scope.REQUEST)
    def local_document_converter_producer(
        self,
        html_to_pdf: HtmlToPdfRendererProtocol,
        markdown_to_html: MarkdownToHtmlRendererProtocol,
        pdf_text_extractor: PdfTextExtractorProtocol,
    ) -> LocalDocumentConverterProducerProtocol:
        return LocalDocumentConverterProducer(
            html_to_pdf=html_to_pdf,
            markdown_to_html=markdown_to_html,
            pdf_text_extractor=pdf_text_extractor,
        )

    @provide(scope=Scope.REQUEST)
    def create_document_converter_jobs_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        policy: DocumentConverterProducerPolicy,
        local_producer: LocalDocumentConverterProducerProtocol,
        local_artifacts: DocumentConverterArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateDocumentConverterJobsHandler:
        return CreateDocumentConverterJobsHandler(
            jobs=jobs,
            client=client,
            policy=policy,
            local_producer=local_producer,
            local_artifacts=local_artifacts,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def list_document_converter_saved_files_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
    ) -> ListDocumentConverterSavedFilesHandler:
        return ListDocumentConverterSavedFilesHandler(
            vault_files=vault_files,
            vault_storage=vault_storage,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def submit_document_converter_saved_file_handler(
        self,
        create_jobs: CreateDocumentConverterJobsHandler,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
    ) -> SubmitDocumentConverterSavedFileHandler:
        return SubmitDocumentConverterSavedFileHandler(
            create_jobs=create_jobs,
            vault_files=vault_files,
            vault_storage=vault_storage,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def render_document_converter_project_preview_handler(
        self,
        renderer: DocumentConverterProjectPreviewRendererProtocol,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> RenderDocumentConverterProjectPreviewHandler:
        return RenderDocumentConverterProjectPreviewHandler(
            renderer=renderer,
            previews=previews,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def get_document_converter_project_preview_handler(
        self,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
    ) -> GetDocumentConverterProjectPreviewHandler:
        return GetDocumentConverterProjectPreviewHandler(previews=previews, clock=clock)

    @provide(scope=Scope.REQUEST)
    def download_document_converter_project_preview_artifact_handler(
        self,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
    ) -> DownloadDocumentConverterProjectPreviewArtifactHandler:
        return DownloadDocumentConverterProjectPreviewArtifactHandler(
            previews=previews,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def discard_document_converter_project_preview_handler(
        self,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
    ) -> DiscardDocumentConverterProjectPreviewHandler:
        return DiscardDocumentConverterProjectPreviewHandler(previews=previews, clock=clock)

    @provide(scope=Scope.REQUEST)
    def cleanup_document_converter_project_previews_handler(
        self,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        clock: ClockProtocol,
    ) -> CleanupDocumentConverterProjectPreviewsHandler:
        return CleanupDocumentConverterProjectPreviewsHandler(previews=previews, clock=clock)

    @provide(scope=Scope.REQUEST)
    def save_document_converter_project_preview_artifact_handler(
        self,
        previews: DocumentConverterProjectPreviewStoreProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> SaveDocumentConverterProjectPreviewArtifactHandler:
        return SaveDocumentConverterProjectPreviewArtifactHandler(
            previews=previews,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def get_document_converter_job_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> GetDocumentConverterJobHandler:
        return GetDocumentConverterJobHandler(
            jobs=jobs,
            client=client,
            uow=uow,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def download_document_converter_artifact_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        local_artifacts: DocumentConverterArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> DownloadDocumentConverterArtifactHandler:
        return DownloadDocumentConverterArtifactHandler(
            jobs=jobs,
            client=client,
            local_artifacts=local_artifacts,
            uow=uow,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def save_document_converter_artifact_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        local_artifacts: DocumentConverterArtifactStoreProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> SaveDocumentConverterArtifactHandler:
        return SaveDocumentConverterArtifactHandler(
            jobs=jobs,
            client=client,
            local_artifacts=local_artifacts,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
            settings=settings,
        )
