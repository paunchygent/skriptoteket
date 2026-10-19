"""DI bindings for native exam workspace conversion and import (ST-SKRIPT-39-04).

The content classifier, DOCX conversion pipeline, conversion progress/status,
retry, and DigiExam/DOCX import handlers. These request-scoped handlers share
the request session, UoW, and vault repositories with the document editing
provider; the container resolves their document-store dependencies across the
two providers.
"""

from __future__ import annotations

import httpx
from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.exam_content_tagging import (
    MeteredExamContentTagClassifier,
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
    ImportExamWorkspaceDigiExamDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_misspellings import (
    GenerateExamWorkspaceMisspellingsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
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
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
    GetExamContentSuggestionsHandlerProtocol,
    GetExamCourseCatalogHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    RequestExamContentSuggestionsHandlerProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import ProfileRepositoryProtocol, UserRepositoryProtocol
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


class ExamWorkspaceConversionProvider(Provider):
    """Provide exam workspace conversion, import, and progress handlers."""

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
