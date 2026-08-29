"""In-process Exam Converter producer service.

Purpose:
    Convert one uploaded DigiExam `.dxe` export into the Exam.net bundle
    artifact (QTI package, Exam.net-profile PDF, QTI validation report) using
    the ported exam-conversion domain chain, optionally applying one
    source-bound teacher ingestion overlay.

Relationships:
    Implements ``InProcessExamConverterProtocol`` for
    ``application.curated_apps.handlers.exam_converter_conversions``. Uses the
    ``domain.curated_apps.exam_conversion`` chain plus the QTI package writer
    and Exam.net PDF renderer infrastructure seams.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from skriptoteket.application.curated_apps.exam_conversion import (
    EXAMNET_BUNDLE_PDF_FILENAME,
    EXAMNET_BUNDLE_QTI_PACKAGE_FILENAME,
    EXAMNET_BUNDLE_QTI_VALIDATION_REPORT_FILENAME,
    ExamConversionStoredArtifact,
    build_examnet_bundle_filename,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamParseStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import (
    DigiExamDxeParser,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf import (
    build_digiexam_examnet_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay import (
    parse_and_apply_digiexam_ingestion_overlay,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay_contracts import (
    DigiExamIngestionOverlayError,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
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
        upload: "ConversionHubUpload",
        overlay_bytes: bytes | None,
        correlation_id: str | None,
        overlay_key_provenance: DigiExamAnswerKeyProvenance = (
            DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY
        ),
    ) -> ExamConversionStoredArtifact:
        """Convert one upload through the in-process exam-conversion chain.

        Args:
            upload: Uploaded `.dxe` payload.
            overlay_bytes: Optional source-bound ingestion overlay.
            correlation_id: Request correlation id.
            overlay_key_provenance: What applied overlay keys represent:
                teacher-provided (default) or machine-proposed.

        Returns:
            The Exam.net bundle artifact (QTI package, PDF, validation report).

        Raises:
            DomainError: If the source cannot be parsed, the overlay does not
                bind to this source, or manual follow-ups block both targets.
        """
        del correlation_id
        exam = parse_source_exam(upload=upload)
        effective_exam = _apply_overlay(
            exam=exam,
            upload=upload,
            overlay_bytes=overlay_bytes,
            overlay_key_provenance=overlay_key_provenance,
        )
        plan = _build_qti_package_plan(exam=effective_exam, input_filename=upload.filename)
        qti_package_bytes = self._qti_writer.build_package_bytes(plan)
        pdf_bytes = self._build_pdf_bytes(exam=effective_exam)
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
        return ExamConversionStoredArtifact(
            filename=build_examnet_bundle_filename(input_filename=upload.filename),
            content_type=_BUNDLE_CONTENT_TYPE,
            content=bundle_bytes,
        )

    def _build_pdf_bytes(self, *, exam: DigiExamIntermediateExam) -> bytes:
        document = build_digiexam_examnet_pdf_document(exam)
        if document.status is not DigiExamExamNetPdfStatus.SUCCESS:
            raise validation_error(_MANUAL_FOLLOW_UP_MESSAGE)
        return self._pdf_renderer.render_pdf(document=document)


def source_exam_digests(*, file_bytes: bytes, exam: DigiExamIntermediateExam) -> tuple[str, str]:
    """Return the deterministic source-file and source-IR digests for one exam."""
    source_file_sha256 = f"sha256:{hashlib.sha256(file_bytes).hexdigest()}"
    ir_payload = _json_bytes(_json_ready(asdict(exam)))
    source_ir_sha256 = f"sha256:{hashlib.sha256(ir_payload).hexdigest()}"
    return source_file_sha256, source_ir_sha256


def parse_source_exam(*, upload: "ConversionHubUpload") -> DigiExamIntermediateExam:
    """Parse one uploaded `.dxe` export into the renderer-neutral IR."""
    try:
        text = upload.file_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise validation_error(_INVALID_DXE_MESSAGE) from exc
    parse_result = DigiExamDxeParser().parse_text(text, filename=upload.filename)
    if parse_result.status is DigiExamParseStatus.BLOCKED and not parse_result.items:
        raise validation_error(_INVALID_DXE_MESSAGE)
    return build_digiexam_intermediate_exam(parse_result)


def _apply_overlay(
    *,
    exam: DigiExamIntermediateExam,
    upload: "ConversionHubUpload",
    overlay_bytes: bytes | None,
    overlay_key_provenance: DigiExamAnswerKeyProvenance,
) -> DigiExamIntermediateExam:
    if overlay_bytes is None:
        return exam
    source_file_sha256, source_ir_sha256 = source_exam_digests(
        file_bytes=upload.file_bytes,
        exam=exam,
    )
    try:
        overlay_result = parse_and_apply_digiexam_ingestion_overlay(
            overlay_bytes=overlay_bytes,
            source_file_sha256=source_file_sha256,
            source_ir_sha256=source_ir_sha256,
            source_exam=exam,
            applied_key_provenance=overlay_key_provenance,
        )
    except DigiExamIngestionOverlayError as exc:
        raise validation_error(str(exc)) from exc
    return overlay_result.effective_exam_for_rendering


def _build_qti_package_plan(
    *, exam: DigiExamIntermediateExam, input_filename: str
) -> ExamNetQtiPackagePlan:
    adapter_result = build_examnet_qti_items_from_digiexam_ir(exam)
    if adapter_result.manual_follow_ups:
        raise validation_error(_MANUAL_FOLLOW_UP_MESSAGE)
    plan = build_examnet_qti_package_plan(
        package_name=_package_name(input_filename),
        items=adapter_result.items,
    )
    if plan.status is not ExamNetQtiPackageStatus.PASSED:
        raise validation_error(_MANUAL_FOLLOW_UP_MESSAGE)
    return plan


def _package_name(input_filename: str) -> str:
    return input_filename.rsplit(".", 1)[0] if "." in input_filename else input_filename


def _json_bytes(payload: object) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return f"{text}\n".encode("utf-8")


def _json_ready(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_ready(asdict(value))
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_ready(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_ready(child) for child in value]
    return value
