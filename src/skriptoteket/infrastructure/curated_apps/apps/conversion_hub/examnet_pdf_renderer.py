"""Exam.net-oriented DigiExam PDF renderer for the in-process lane.

Purpose:
    Materialize the exam-conversion domain PDF document plan (HTML plus image
    assets) as PDF bytes through the shared WeasyPrint call pattern.

Relationships:
    Implements ``ExamNetPdfRendererProtocol`` for the in-process Exam
    Converter producer and delegates the WeasyPrint call to
    ``infrastructure.documents.pdf_rendering``.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfDocument,
    DigiExamExamNetPdfStatus,
)
from skriptoteket.infrastructure.documents.pdf_rendering import render_html_to_pdf_bytes
from skriptoteket.protocols.exam_conversion import ExamNetPdfRendererProtocol


class WeasyPrintExamNetPdfRenderer(ExamNetPdfRendererProtocol):
    """Render one successful Exam.net PDF document plan into PDF bytes."""

    def render_pdf(self, *, document: DigiExamExamNetPdfDocument) -> bytes:
        """Render the document HTML with its image assets into PDF bytes.

        Args:
            document: A successful exam-conversion PDF document plan.

        Returns:
            The rendered PDF payload.

        Raises:
            ValueError: If the document plan is not renderable.
        """
        if document.status is not DigiExamExamNetPdfStatus.SUCCESS:
            raise ValueError("Only successful Exam.net PDF document plans can be rendered.")
        with tempfile.TemporaryDirectory(prefix="examnet-pdf-") as work_dir_name:
            work_dir = Path(work_dir_name)
            for asset_file in document.asset_files:
                asset_path = work_dir / asset_file.relative_path
                asset_path.parent.mkdir(parents=True, exist_ok=True)
                asset_path.write_bytes(asset_file.payload)
            return render_html_to_pdf_bytes(
                html=document.html,
                base_url=f"{work_dir.resolve().as_uri()}/",
            )
