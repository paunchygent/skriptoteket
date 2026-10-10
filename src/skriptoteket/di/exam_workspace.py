"""DI bindings for the native exam workspace (ST-SKRIPT-39-04).

A focused provider: the DOCX chunker and container codec are stateless
app-scoped adapters; the document store and handlers are request-scoped so
they share the request session, UoW, and vault repositories.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
    GetExamWorkspaceConversionStatusHandler,
    GetExamWorkspaceDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
    ListExamWorkspaceDocumentsHandler,
    SaveExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_proposal_carry_forward import (
    CarryExamWorkspaceProposals,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
)
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
from skriptoteket.infrastructure.llm.answer_key_provider_selection import (
    FixedRouteAnswerKeyProviderSelector,
)
from skriptoteket.infrastructure.llm.openai.docx_conversion_profiles import (
    build_luna_docx_conversion_profile,
)
from skriptoteket.infrastructure.llm.openrouter.answer_key_profiles import (
    build_glm_failover_answer_key_profile,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamAnswerKeyProposedOverlayRepositoryProtocol,
)
from skriptoteket.protocols.exam_workspace import (
    DocxExamChunkerProtocol,
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
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
    def docx_converter(
        self,
        provider: AnswerKeyStructuredProviderProtocol,
        leases: AnswerKeyTokenLeaseRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
    ) -> DocxAIConverter:
        return DocxAIConverter(
            provider=provider,
            provider_selector=FixedRouteAnswerKeyProviderSelector(
                route=AnswerKeyProviderRoute(
                    primary=build_luna_docx_conversion_profile(settings),
                    failover=build_glm_failover_answer_key_profile(settings),
                )
            ),
            leases=leases,
            uow=uow,
            clock=clock,
            enabled=settings.LLM_ANSWER_KEY_ENABLED,
        )

    @provide(scope=Scope.REQUEST)
    def process_docx_job(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        chunker: DocxExamChunkerProtocol,
        converter: DocxAIConverter,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        users: UserRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ProcessExamWorkspaceDocxJobHandler:
        return ProcessExamWorkspaceDocxJobHandler(
            jobs=jobs,
            chunker=chunker,
            converter=converter,
            codec=codec,
            store=store,
            users=users,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def conversion_status_handler(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ) -> GetExamWorkspaceConversionStatusHandler:
        return GetExamWorkspaceConversionStatusHandler(jobs=jobs)

    @provide(scope=Scope.APP)
    def container_codec(self) -> ExamWorkspaceContainerCodecProtocol:
        """Provide the fail-closed container codec."""
        return ExamWorkspaceContainerCodec()

    @provide(scope=Scope.REQUEST)
    def proposal_carry_forward(
        self,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        proposed_overlays: ExamAnswerKeyProposedOverlayRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CarryExamWorkspaceProposals:
        """Provide save-time copying of pending proposals without execution."""
        return CarryExamWorkspaceProposals(
            enrichment_jobs=enrichment_jobs,
            proposed_overlays=proposed_overlays,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def document_store(
        self,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        proposal_carry_forward: CarryExamWorkspaceProposals,
    ) -> ExamWorkspaceDocumentStore:
        """Provide the versioned Mina filer document store."""
        return ExamWorkspaceDocumentStore(
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=uow,
            clock=clock,
            settings=settings,
            proposal_carry_forward=proposal_carry_forward,
        )

    @provide(scope=Scope.REQUEST)
    def import_handler(
        self,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        id_generator: IdGeneratorProtocol,
    ) -> ImportExamWorkspaceDocumentHandler:
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
    ) -> GetExamWorkspaceDocumentHandler:
        """Provide the reopen handler."""
        return GetExamWorkspaceDocumentHandler(vault_files=vault_files, codec=codec, store=store)

    @provide(scope=Scope.REQUEST)
    def list_handler(
        self, vault_files: VaultFileRepositoryProtocol
    ) -> ListExamWorkspaceDocumentsHandler:
        """Provide the head-version document list handler."""
        return ListExamWorkspaceDocumentsHandler(vault_files=vault_files)

    @provide(scope=Scope.REQUEST)
    def export_handler(
        self,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> ExportExamWorkspaceDocumentHandler:
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
    ) -> SaveExamWorkspaceDocumentHandler:
        """Provide the versioned save handler."""
        return SaveExamWorkspaceDocumentHandler(
            vault_files=vault_files, codec=codec, store=store, id_generator=id_generator
        )
