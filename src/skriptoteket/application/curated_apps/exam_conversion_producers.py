"""In-process Exam Converter producer service.

Purpose:
    Convert one uploaded DigiExam `.dxe` export into the Exam.net bundle
    artifact (QTI package, Exam.net-profile PDF, QTI validation report) using
    the ported exam-conversion domain chain for the public guest converter.

Relationships:
    Implements ``PublicInProcessExamConverterProtocol`` for
    ``application.curated_apps.public_exam_converter_local_execution``. Uses the
    ``domain.curated_apps.exam_conversion`` chain plus the QTI package writer
    and Exam.net PDF renderer infrastructure seams. ``parse_source_exam`` is
    shared with the exam workspace.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_conversion import (
    EXAMNET_BUNDLE_PDF_FILENAME,
    EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME,
    EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME,
    ExamConversionStoredArtifact,
    build_examnet_bundle_filename,
)
from skriptoteket.application.curated_apps.exam_conversion_review_artifacts import (
    build_review_named_artifacts,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamParseStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import (
    DigiExamDxeParser,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf import (
    build_digiexam_examnet_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfDocument,
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.protocols.exam_conversion import (
    ExamNetPdfRendererProtocol,
    ExamNetQtiPackageWriterProtocol,
)

if TYPE_CHECKING:
    from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
        ConversionHubUpload,
    )

_BUNDLE_CONTENT_TYPE = "application/zip"
_INVALID_DXE_MESSAGE = "Filen kunde inte tolkas som en DigiExam-export (.dxe)."
_MANUAL_FOLLOW_UP_MESSAGE = (
    "Provet kan inte konverteras automatiskt ännu: frågor saknar facit eller "
    "har en frågetyp som inte stöds. Komplettera provet och försök igen."
)


class InProcessExamConversionProducer:
    """Produce the Exam.net bundle for one `.dxe` upload inside Skriptoteket."""

    def __init__(
        self,
        *,
        qti_writer: ExamNetQtiPackageWriterProtocol,
        pdf_renderer: ExamNetPdfRendererProtocol,
    ) -> None:
        self._qti_writer = qti_writer
        self._pdf_renderer = pdf_renderer

    async def convert(
        self,
        *,
        job_id: UUID,
        upload: "ConversionHubUpload",
        answer_evidence: DigiExamResultPdfAnswerEvidence | None,
        enrichment_failure_code: str | None,
        correlation_id: str | None,
    ) -> ExamConversionStoredArtifact:
        """Convert one upload through the in-process exam-conversion chain.

        Args:
            job_id: Local job id bound into the review artifacts.
            upload: Uploaded `.dxe` payload.
            answer_evidence: Optional graded-result evidence supplying answer keys.
            enrichment_failure_code: When set, emit the manual-follow-up bundle
                carrying this code instead of converting.
            correlation_id: Request correlation id.

        Returns:
            The Exam.net bundle artifact (QTI package, PDF, validation report).

        Raises:
            DomainError: If the source cannot be parsed or manual follow-ups
                block both targets.
        """
        del correlation_id
        exam = parse_source_exam(upload=upload, answer_evidence=answer_evidence)
        if enrichment_failure_code is not None:
            pdf_bytes = self._pdf_renderer.render_pdf(
                document=DigiExamExamNetPdfDocument(
                    status=DigiExamExamNetPdfStatus.SUCCESS,
                    html=(
                        "<!doctype html><html lang='sv'><meta charset='utf-8'>"
                        "<title>Manuell granskning krävs</title>"
                        "<body><h1>Manuell granskning krävs</h1>"
                        "<p>Facit behöver kompletteras innan export.</p></body></html>"
                    ),
                    asset_files=(),
                    warnings=(),
                )
            )
            report_bytes = _json_bytes(
                {
                    "schema_version": "qti_validation_report_v1",
                    "status": "manual_follow_up_required",
                    "failure_code": enrichment_failure_code,
                }
            )
            qti_package_bytes = self._qti_writer.build_bundle_bytes(
                entries=(("manual-follow-up.json", report_bytes),)
            )
        else:
            pdf_bytes = self._build_pdf_bytes(exam=exam)
            plan = _build_qti_package_plan(exam=exam, input_filename=upload.filename)
            qti_package_bytes = self._qti_writer.build_package_bytes(plan)
            report_bytes = self._qti_writer.build_validation_report_bytes(
                plan=plan,
                package_filename=EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME,
                package_bytes=qti_package_bytes,
            )
        bundle_bytes = self._qti_writer.build_bundle_bytes(
            entries=(
                (EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME, qti_package_bytes),
                (EXAMNET_BUNDLE_PDF_FILENAME, pdf_bytes),
                (EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME, report_bytes),
            )
        )
        named_artifacts = build_review_named_artifacts(
            job_id=job_id,
            source_exam=exam,
            enrichment_failure_code=enrichment_failure_code,
            qti_package_bytes=qti_package_bytes,
            pdf_bytes=pdf_bytes,
            validation_report_bytes=report_bytes,
        )
        return ExamConversionStoredArtifact(
            filename=build_examnet_bundle_filename(input_filename=upload.filename),
            content_type=_BUNDLE_CONTENT_TYPE,
            content=bundle_bytes,
            source_filename=upload.filename,
            source_content=upload.file_bytes,
            named_artifacts=named_artifacts,
        )

    def _build_pdf_bytes(self, *, exam: DigiExamIntermediateExam) -> bytes:
        document = build_digiexam_examnet_pdf_document(exam)
        if document.status is not DigiExamExamNetPdfStatus.SUCCESS:
            raise validation_error(_MANUAL_FOLLOW_UP_MESSAGE)
        return self._pdf_renderer.render_pdf(document=document)


def parse_source_exam(
    *,
    upload: "ConversionHubUpload",
    answer_evidence: DigiExamResultPdfAnswerEvidence | None = None,
) -> DigiExamIntermediateExam:
    """Parse one uploaded `.dxe` export into the renderer-neutral IR."""
    try:
        text = upload.file_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise validation_error(_INVALID_DXE_MESSAGE) from exc
    parse_result = DigiExamDxeParser().parse_text(
        text,
        filename=upload.filename,
        answer_evidence=answer_evidence,
    )
    if parse_result.status is DigiExamParseStatus.BLOCKED and not parse_result.items:
        raise validation_error(_INVALID_DXE_MESSAGE)
    return build_digiexam_intermediate_exam(parse_result)


def _build_qti_package_plan(
    *, exam: DigiExamIntermediateExam, input_filename: str
) -> ExamNetQtiPackagePlan:
    adapter_result = build_examnet_qti_items_from_digiexam_ir(exam)
    if adapter_result.manual_follow_ups:
        raise validation_error(_MANUAL_FOLLOW_UP_MESSAGE)
    # A DigiExam upload carries no exam title; the upload's own name is the source's name.
    source_name = _package_name(input_filename)
    plan = build_examnet_qti_package_plan(
        package_name=source_name,
        items=adapter_result.items,
        assessment_title=source_name,
    )
    if plan.status is not ExamNetQtiPackageStatus.PASSED:
        raise validation_error(_MANUAL_FOLLOW_UP_MESSAGE)
    return plan


def _package_name(input_filename: str) -> str:
    return input_filename.rsplit(".", 1)[0] if "." in input_filename else input_filename


def _json_bytes(payload: JsonValue) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return f"{text}\n".encode("utf-8")
