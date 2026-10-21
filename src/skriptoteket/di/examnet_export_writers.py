"""DI bindings for the Exam.net export writers.

Provides the Exam.net QTI package writer and the Exam.net PDF renderer for
exam workspace exports.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.exam_conversion import (
    ExamNetPdfRendererProtocol,
    ExamNetQtiPackageWriterProtocol,
)


class ExamNetExportWritersProvider(Provider):
    """Provide Exam.net export writers for the exam workspace."""

    @provide(scope=Scope.APP)
    def examnet_qti_package_writer(self) -> ExamNetQtiPackageWriterProtocol:
        return ExamNetQtiPackageWriter()

    @provide(scope=Scope.APP)
    def examnet_pdf_renderer(self) -> ExamNetPdfRendererProtocol:
        return WeasyPrintExamNetPdfRenderer()
