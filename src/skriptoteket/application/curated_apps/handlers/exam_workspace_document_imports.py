"""Exam workspace document import handlers: Word or PDF, and DigiExam intake.

Import queues one teacher file as a background conversion. Each exam has one
saved vault file and a separate bounded editor history. Persistence and
storage accounting live in ``exam_workspace_document_store``.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    ExamWorkspaceConversionJobView,
)
from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceConversionStatus,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    conversion_status,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.import_file_format import is_pdf
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.docx_conversion_progress import ConversionPhase
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def validated_exam_course(course_key: str | None) -> ExamCourseChoice | None:
    """Return the catalog course for a chosen key, or ``None`` when none is chosen.

    A key over 64 characters and a key absent from the catalog raise the same
    Swedish validation errors the import routes have always returned.
    """

    selected_course_key = (course_key or "").strip() or None
    if selected_course_key is None:
        return None
    if len(selected_course_key) > 64:
        raise validation_error(
            "Kurskoden får vara högst 64 tecken.", details={"field": "course_key"}
        )
    course = next(
        (
            course
            for course in load_exam_course_catalog().courses
            if course.key == selected_course_key
        ),
        None,
    )
    if course is None:
        raise validation_error("Välj en kurs ur kurslistan.", details={"field": "course_key"})
    return ExamCourseChoice(key=course.key, name=course.name)


class ImportExamWorkspaceDocumentHandler:
    """Import one teacher Word file or text PDF into a new exam workspace document.

    A PDF runs the Word conversion lane unchanged (ST-SKRIPT-39-10 P5): its bytes travel
    in the job's ``source_docx`` and the lane's chunker reads them by their format.
    """

    extensions: tuple[str, ...] = (".docx", ".pdf")
    source_kind = ExamAnswerKeySourceKind.DOCX_IMPORT

    def __init__(
        self,
        *,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        settings: Settings,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._uow = uow
        self._clock = clock
        self._settings = settings
        self._id_generator = id_generator

    async def handle(
        self, *, actor: User, filename: str, content: bytes, course_key: str | None
    ) -> ExamWorkspaceConversionStatus:
        safe_name = sanitize_input_filename(input_filename=filename)
        if not safe_name.lower().endswith(self.extensions):
            choices = " eller ".join(f"{extension}-fil" for extension in self.extensions)
            raise validation_error(f"Välj en {choices}.", details={"filename": safe_name})
        if not content:
            raise validation_error("Filen saknar innehåll.")
        if safe_name.lower().endswith(".pdf") and not is_pdf(content):
            raise validation_error(
                "Filen kunde inte läsas som en PDF-fil (.pdf).", details={"filename": safe_name}
            )
        if len(content) > self._settings.VAULT_MAX_FILE_BYTES:
            raise validation_error("Filen är större än maxstorleken för Mina filer.")

        course = validated_exam_course(course_key)
        selected_course_key = None if course is None else course.key

        document_id = self._id_generator.new_uuid()
        now = self._clock.now()
        # A Word or PDF import is queued already reading, so the teacher's first poll
        # shows the phase and its clock starts at the upload; the worker's claim comes later.
        reading = self.source_kind is ExamAnswerKeySourceKind.DOCX_IMPORT
        async with self._uow:
            job = await self._jobs.create(
                job=ExamAnswerKeyEnrichmentJob(
                    id=self._id_generator.new_uuid(),
                    source_kind=self.source_kind,
                    owner_user_id=actor.id,
                    status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
                    input_filename=safe_name,
                    source_docx=content
                    if self.source_kind is ExamAnswerKeySourceKind.DOCX_IMPORT
                    else None,
                    source_dxe=content
                    if self.source_kind is ExamAnswerKeySourceKind.DIGIEXAM_IMPORT
                    else None,
                    workspace_lineage_id=document_id,
                    workspace_document_revision=1,
                    workspace_course_key=selected_course_key,
                    conversion_phase=ConversionPhase.READING if reading else None,
                    conversion_phase_started_at=now if reading else None,
                    available_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
        return conversion_status(
            ExamWorkspaceConversionJobView.model_validate(job, from_attributes=True)
        )


class ImportExamWorkspaceDigiExamDocumentHandler(ImportExamWorkspaceDocumentHandler):
    """Queue a bare DigiExam export without invoking answer-key enrichment."""

    extensions = (".dxe",)
    source_kind = ExamAnswerKeySourceKind.DIGIEXAM_IMPORT
