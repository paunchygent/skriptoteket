"""DI bindings for the Exam Converter curated app.

Exam conversion writers, renderers, artifact store, in-process converters,
correction-session repositories and handlers, and the public exam converter
job store and runtime handlers.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
)
from skriptoteket.application.curated_apps.handlers.document_converter_vault_saves import (
    DocumentConverterVaultSaveService,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_conversions import (
    CreateExamConverterConversionJobsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_correction_sessions import (
    GetExamConverterCorrectionSessionHandler,
    ReplaceExamConverterCorrectionIntentsHandler,
    RevertExamConverterCorrectionIntentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_product import (
    ExamConverterProductHandler,
    SaveExamConverterLocalArtifactHandler,
)
from skriptoteket.application.curated_apps.handlers.public_exam_converter_jobs import (
    PublicExamConverterRuntimeHandler,
)
from skriptoteket.application.curated_apps.public_exam_converter_local_execution import (
    ProcessPublicExamConverterJobHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_conversion_artifacts import (
    FilesystemExamConversionArtifactStore,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.infrastructure.repositories.conversion_hub_jobs import (
    PostgreSQLConversionHubJobRepository,
)
from skriptoteket.infrastructure.repositories.exam_converter_correction_sessions import (
    PostgreSQLExamConverterCorrectionSessionRepository,
)
from skriptoteket.infrastructure.repositories.public_exam_converter_jobs import (
    PostgreSQLPublicExamConverterJobRepository,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import (
    ConversionHubJobRepositoryProtocol,
    ExamConverterSubmissionRepositoryProtocol,
)
from skriptoteket.protocols.documents import PdfTextExtractorProtocol
from skriptoteket.protocols.exam_answer_key import (
    ExamAnswerKeyEnrichmentJobRepositoryProtocol,
    ExamAnswerKeyProposedOverlayRepositoryProtocol,
)
from skriptoteket.protocols.exam_conversion import (
    ExamConversionArtifactStoreProtocol,
    ExamNetPdfRendererProtocol,
    ExamNetQtiPackageWriterProtocol,
    InProcessExamConverterProtocol,
    PublicInProcessExamConverterProtocol,
)
from skriptoteket.protocols.exam_converter_correction_sessions import (
    ExamConverterCorrectionMutationRepositoryProtocol,
    ExamConverterCorrectionSessionRepositoryProtocol,
    ExamConverterReplayCorrectionSessionRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.public_exam_converter import PublicExamConverterJobStoreProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class ExamConverterProvider(Provider):
    """Provide Exam Converter adapters, repositories, and application handlers."""

    @provide(scope=Scope.REQUEST)
    def public_exam_converter_job_store(
        self,
        session: AsyncSession,
    ) -> PublicExamConverterJobStoreProtocol:
        return PostgreSQLPublicExamConverterJobRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def exam_converter_submission_repository(
        self, session: AsyncSession
    ) -> ExamConverterSubmissionRepositoryProtocol:
        return PostgreSQLConversionHubJobRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def exam_converter_correction_session_repository(
        self,
        session: AsyncSession,
    ) -> ExamConverterCorrectionSessionRepositoryProtocol:
        return PostgreSQLExamConverterCorrectionSessionRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def exam_converter_replay_correction_session_repository(
        self, session: AsyncSession
    ) -> ExamConverterReplayCorrectionSessionRepositoryProtocol:
        return PostgreSQLExamConverterCorrectionSessionRepository(session=session)

    @provide(scope=Scope.REQUEST)
    def exam_converter_correction_mutation_repository(
        self, session: AsyncSession
    ) -> ExamConverterCorrectionMutationRepositoryProtocol:
        return PostgreSQLExamConverterCorrectionSessionRepository(session=session)

    @provide(scope=Scope.APP)
    def examnet_qti_package_writer(self) -> ExamNetQtiPackageWriterProtocol:
        return ExamNetQtiPackageWriter()

    @provide(scope=Scope.APP)
    def examnet_pdf_renderer(self) -> ExamNetPdfRendererProtocol:
        return WeasyPrintExamNetPdfRenderer()

    @provide(scope=Scope.APP)
    def exam_conversion_artifact_store(
        self,
        settings: Settings,
    ) -> ExamConversionArtifactStoreProtocol:
        return FilesystemExamConversionArtifactStore(artifacts_root=settings.ARTIFACTS_ROOT)

    @provide(scope=Scope.APP)
    def in_process_exam_converter(
        self,
        qti_writer: ExamNetQtiPackageWriterProtocol,
        pdf_renderer: ExamNetPdfRendererProtocol,
    ) -> InProcessExamConverterProtocol:
        return InProcessExamConversionProducer(
            qti_writer=qti_writer,
            pdf_renderer=pdf_renderer,
        )

    @provide(scope=Scope.APP)
    def public_in_process_exam_converter(
        self,
        qti_writer: ExamNetQtiPackageWriterProtocol,
        pdf_renderer: ExamNetPdfRendererProtocol,
    ) -> PublicInProcessExamConverterProtocol:
        return InProcessExamConversionProducer(
            qti_writer=qti_writer,
            pdf_renderer=pdf_renderer,
        )

    @provide(scope=Scope.REQUEST)
    def create_exam_converter_conversion_jobs_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        submission_lookup: ExamConverterSubmissionRepositoryProtocol,
        producer: InProcessExamConverterProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        enrichment_jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateExamConverterConversionJobsHandler:
        return CreateExamConverterConversionJobsHandler(
            jobs=jobs,
            submission_lookup=submission_lookup,
            producer=producer,
            artifacts=artifacts,
            enrichment_jobs=enrichment_jobs,
            enrichment_enabled=settings.LLM_ANSWER_KEY_ENABLED,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def exam_converter_product_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        sessions: ExamConverterReplayCorrectionSessionRepositoryProtocol,
        proposals: ExamAnswerKeyProposedOverlayRepositoryProtocol,
        producer: InProcessExamConverterProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
    ) -> ExamConverterProductHandler:
        return ExamConverterProductHandler(
            jobs=jobs,
            sessions=sessions,
            proposals=proposals,
            producer=producer,
            artifacts=artifacts,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def save_exam_converter_local_artifact_handler(
        self,
        product: ExamConverterProductHandler,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        settings: Settings,
    ) -> SaveExamConverterLocalArtifactHandler:
        return SaveExamConverterLocalArtifactHandler(
            product=product,
            vault_saves=DocumentConverterVaultSaveService(
                vault_files=vault_files,
                vault_usage=vault_usage,
                vault_storage=vault_storage,
                uow=uow,
                clock=clock,
                id_generator=id_generator,
                settings=settings,
            ),
        )

    @provide(scope=Scope.REQUEST)
    def get_exam_converter_correction_session_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        sessions: ExamConverterCorrectionSessionRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> GetExamConverterCorrectionSessionHandler:
        return GetExamConverterCorrectionSessionHandler(
            jobs=jobs,
            sessions=sessions,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def replace_exam_converter_correction_intents_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        sessions: ExamConverterCorrectionMutationRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ReplaceExamConverterCorrectionIntentsHandler:
        return ReplaceExamConverterCorrectionIntentsHandler(
            jobs=jobs,
            sessions=sessions,
            uow=uow,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def revert_exam_converter_correction_intent_handler(
        self,
        jobs: ConversionHubJobRepositoryProtocol,
        sessions: ExamConverterCorrectionMutationRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> RevertExamConverterCorrectionIntentHandler:
        return RevertExamConverterCorrectionIntentHandler(
            jobs=jobs,
            sessions=sessions,
            uow=uow,
        )

    @provide(scope=Scope.REQUEST)
    def public_exam_converter_runtime_handler(
        self,
        store: PublicExamConverterJobStoreProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> PublicExamConverterRuntimeHandler:
        return PublicExamConverterRuntimeHandler(
            store=store,
            artifacts=artifacts,
            uow=uow,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def process_public_exam_converter_job_handler(
        self,
        store: PublicExamConverterJobStoreProtocol,
        producer: PublicInProcessExamConverterProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        pdf_text_extractor: PdfTextExtractorProtocol,
        clock: ClockProtocol,
        uow: UnitOfWorkProtocol,
    ) -> ProcessPublicExamConverterJobHandler:
        return ProcessPublicExamConverterJobHandler(
            store=store,
            producer=producer,
            artifacts=artifacts,
            pdf_text_extractor=pdf_text_extractor,
            clock=clock,
            uow=uow,
        )
