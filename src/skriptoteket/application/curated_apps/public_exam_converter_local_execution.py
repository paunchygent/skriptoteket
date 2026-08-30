"""Worker-side execution for durable public Exam Converter jobs."""

from __future__ import annotations

import logging
from dataclasses import replace

from skriptoteket.application.curated_apps.exam_conversion_producers import parse_source_exam
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterJobStatus,
    PublicExamConverterSubmittedJob,
    PublicExamConverterUpload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    AnswerKeyEnrichmentPlanState,
    plan_answer_key_enrichment,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamSourceLine,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
    DigiExamResultPdfAnswerExtractor,
    normalize_result_text,
)
from skriptoteket.domain.errors import DomainError, validation_error
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.documents import PdfTextExtractorProtocol
from skriptoteket.protocols.exam_conversion import (
    ExamConversionArtifactStoreProtocol,
    PublicInProcessExamConverterProtocol,
)
from skriptoteket.protocols.public_exam_converter import PublicExamConverterJobStoreProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_LOCAL_FAILURE_MESSAGE = "Konverteringen kunde inte genomföras. Försök igen."
_MANUAL_FOLLOW_UP_CODE = "public_manual_follow_up_required"
_ROUTE_KEY = "digiexam_dxe_to_examnet_migration_bundle"

logger = logging.getLogger(__name__)


class ProcessPublicExamConverterJobHandler:
    """Run one claimed public job and publish its terminal state atomically."""

    def __init__(
        self,
        *,
        store: PublicExamConverterJobStoreProtocol,
        producer: PublicInProcessExamConverterProtocol,
        artifacts: ExamConversionArtifactStoreProtocol,
        pdf_text_extractor: PdfTextExtractorProtocol,
        clock: ClockProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._store = store
        self._producer = producer
        self._artifacts = artifacts
        self._pdf_text_extractor = pdf_text_extractor
        self._clock = clock
        self._uow = uow

    async def handle(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
    ) -> PublicExamConverterSubmittedJob:
        """Execute a job already claimed by the PostgreSQL worker."""

        source_dxe = job.source_dxe
        upload = ConversionHubUpload(
            filename=source_dxe.filename,
            content_type=source_dxe.content_type,
            file_bytes=source_dxe.file_bytes,
        )
        try:
            answer_evidence = self._answer_evidence(job.graded_result_pdf)
            exam = parse_source_exam(upload=upload, answer_evidence=answer_evidence)
            plan = plan_answer_key_enrichment(exam)
            artifact = await self._producer.convert(
                job_id=job.local_job_id,
                upload=upload,
                overlay_bytes=None,
                answer_evidence=answer_evidence,
                enrichment_failure_code=(
                    None
                    if plan.state is AnswerKeyEnrichmentPlanState.NOT_NEEDED
                    else _MANUAL_FOLLOW_UP_CODE
                ),
                correlation_id=job.correlation_id,
            )
            self._artifacts.store_artifact(job_id=job.local_job_id, artifact=artifact)
        except DomainError as exc:
            return await self._finish_failed(job=job, message=exc.message)
        except Exception as exc:
            logger.warning(
                "Public Exam Converter local execution failed",
                extra={
                    "public_job_id": job.public_job_id,
                    "error_type": type(exc).__name__,
                },
            )
            return await self._finish_failed(job=job, message=_LOCAL_FAILURE_MESSAGE)

        async with self._uow:
            return await self._store.update(
                job=replace(
                    job,
                    status=PublicExamConverterJobStatus.SUCCEEDED,
                    updated_at=self._clock.now(),
                    locked_by=None,
                    locked_until=None,
                    result={
                        "conversion_metadata": {"route_key": _ROUTE_KEY},
                        "source": {
                            "filename": source_dxe.filename,
                            "format": "digiexam_dxe",
                        },
                        "requested_targets": [target.value for target in job.requested_targets],
                    },
                ),
                expected_worker_id=job.locked_by,
            )

    async def fail_expired(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
    ) -> PublicExamConverterSubmittedJob:
        """Fail-close a job whose processing worker lost its durable lease."""

        return await self._finish_failed(job=job, message=_LOCAL_FAILURE_MESSAGE)

    async def _finish_failed(
        self,
        *,
        job: PublicExamConverterSubmittedJob,
        message: str,
    ) -> PublicExamConverterSubmittedJob:
        async with self._uow:
            return await self._store.update(
                job=replace(
                    job,
                    status=PublicExamConverterJobStatus.FAILED,
                    updated_at=self._clock.now(),
                    locked_by=None,
                    locked_until=None,
                    error_message=message,
                ),
                expected_worker_id=job.locked_by,
            )

    def _answer_evidence(
        self,
        upload: PublicExamConverterUpload | None,
    ) -> DigiExamResultPdfAnswerEvidence | None:
        if upload is None:
            return None
        text = self._pdf_text_extractor.extract_text(
            file_bytes=upload.file_bytes,
            filename=upload.filename,
        )
        if text is None:
            raise validation_error(
                "Det bedömda resultatunderlaget kunde inte läsas på ett säkert sätt."
            )
        raw_lines = tuple(text.splitlines())
        delimiter = _infer_student_block_delimiter(raw_lines)
        if delimiter is None:
            raise validation_error(
                "Det bedömda resultatunderlaget kunde inte klassificeras på ett säkert sätt."
            )
        lines = tuple(
            DigiExamSourceLine(page_number=1, line_number=index, text=value)
            for index, value in enumerate(raw_lines, start=1)
        )
        return DigiExamResultPdfAnswerExtractor(student_block_delimiter=delimiter).extract(lines)


def _infer_student_block_delimiter(lines: tuple[str, ...]) -> str | None:
    counts: dict[str, int] = {}
    for line in lines:
        normalized = normalize_result_text(line)
        if normalized == "" or _looks_like_result_content(normalized):
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
    repeated = tuple((value, count) for value, count in counts.items() if count >= 2)
    if not repeated:
        return None
    return sorted(repeated, key=lambda entry: (-entry[1], entry[0]))[0][0]


def _looks_like_result_content(value: str) -> bool:
    markers = ("Svar", "Erhållen poäng", "Korrekt", "Fel svar", "Max poäng")
    return any(marker in value for marker in markers)
