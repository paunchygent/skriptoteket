"""Exam.net export protocols for the exam workspace.

Purpose:
    Keep the exam workspace export lane protocol-first so deterministic QTI
    packaging and WeasyPrint rendering can evolve independently of FastAPI
    and concrete filesystem code.

Relationships:
    Used by ``application.curated_apps.exam_workspace_exports`` and
    ``application.curated_apps.handlers.exam_workspace_export_renderer``;
    implemented under ``infrastructure.curated_apps.apps.conversion_hub``.
"""

from __future__ import annotations

from typing import Protocol

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfDocument,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackagePlan,
)


class ExamNetQtiPackageWriterProtocol(Protocol):
    """Materialize deterministic QTI package and report bytes from domain plans."""

    def build_package_bytes(self, plan: ExamNetQtiPackagePlan) -> bytes: ...

    def build_validation_report_bytes(
        self,
        *,
        plan: ExamNetQtiPackagePlan,
        package_filename: str,
        package_bytes: bytes | None,
    ) -> bytes: ...


class ExamNetPdfRendererProtocol(Protocol):
    """Render one successful Exam.net PDF document plan into PDF bytes."""

    def render_pdf(self, *, document: DigiExamExamNetPdfDocument) -> bytes: ...
