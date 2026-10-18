"""DI bindings for the Exam Converter curated app.

Exam conversion writers, renderers, artifact store, the public in-process
converter, and the public exam converter job store and runtime handlers.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.exam_conversion_producers import (
    InProcessExamConversionProducer,
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
from skriptoteket.infrastructure.repositories.public_exam_converter_jobs import (
    PostgreSQLPublicExamConverterJobRepository,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.documents import PdfTextExtractorProtocol
from skriptoteket.protocols.exam_conversion import (
    ExamConversionArtifactStoreProtocol,
    ExamNetPdfRendererProtocol,
    ExamNetQtiPackageWriterProtocol,
    PublicInProcessExamConverterProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.public_exam_converter import PublicExamConverterJobStoreProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ExamConverterProvider(Provider):
    """Provide public Exam Converter adapters, repositories, and application handlers."""

    @provide(scope=Scope.REQUEST)
    def public_exam_converter_job_store(
        self,
        session: AsyncSession,
    ) -> PublicExamConverterJobStoreProtocol:
        return PostgreSQLPublicExamConverterJobRepository(session=session)

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
