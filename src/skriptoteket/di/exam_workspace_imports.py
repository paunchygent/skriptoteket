"""DI bindings for exam workspace imports (DOCX, DigiExam, QTI).

Import-lane providers: the DigiExam background job, the DOCX/DigiExam import
handlers, the safe untrusted QTI package reader and the stateless QTI parse
handler plus the signed-in QTI import handler. Request scope shares the
request session; app scope holds the stateless reader and parser.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_imports import (
    ImportExamWorkspaceDigiExamDocumentHandler,
    ImportExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_qti_import import (
    ImportExamWorkspaceQtiDocumentHandler,
    ParseExamWorkspaceQtiPackageHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_package_reader import (  # noqa: E501
    ExamNetQtiPackageReader,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamNetQtiPackageReaderProtocol,
    ExamWorkspaceContainerCodecProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceQtiDocumentHandlerProtocol,
    ParseExamWorkspaceQtiPackageHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ExamWorkspaceImportProvider(Provider):
    """Provide exam workspace import lanes (DOCX, DigiExam, QTI)."""

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

    @provide(scope=Scope.APP)
    def qti_package_reader(self) -> ExamNetQtiPackageReaderProtocol:
        """Provide the safe untrusted QTI package reader."""
        return ExamNetQtiPackageReader()

    @provide(scope=Scope.APP)
    def parse_qti_handler(
        self,
        reader: ExamNetQtiPackageReaderProtocol,
        settings: Settings,
        id_generator: IdGeneratorProtocol,
    ) -> ParseExamWorkspaceQtiPackageHandlerProtocol:
        """Provide the stateless QTI parse handler; it holds no request state."""
        return ParseExamWorkspaceQtiPackageHandler(
            reader=reader, settings=settings, id_generator=id_generator
        )

    @provide(scope=Scope.REQUEST)
    def import_qti_handler(
        self,
        parse: ParseExamWorkspaceQtiPackageHandlerProtocol,
        store: ExamWorkspaceDocumentStore,
        codec: ExamWorkspaceContainerCodecProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ImportExamWorkspaceQtiDocumentHandlerProtocol:
        """Provide the signed-in QTI import handler."""
        return ImportExamWorkspaceQtiDocumentHandler(
            parse=parse, store=store, codec=codec, id_generator=id_generator
        )
