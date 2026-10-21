"""DigiExam source parsing for the exam workspace import.

Purpose:
    Parse one uploaded DigiExam ``.dxe`` export into the renderer-neutral IR
    for the exam workspace import.

Relationships:
    Used by ``application.curated_apps.handlers.exam_workspace_digiexam_jobs``
    when a workspace import carries a DigiExam source file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamParseStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import (
    DigiExamDxeParser,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_result_pdf_answers import (
    DigiExamResultPdfAnswerEvidence,
)
from skriptoteket.domain.errors import validation_error

if TYPE_CHECKING:
    from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
        ConversionHubUpload,
    )

_INVALID_DXE_MESSAGE = "Filen kunde inte tolkas som en DigiExam-export (.dxe)."


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
