"""Serve the packaged Skolverket snapshot without network access."""

from skriptoteket.application.curated_apps.exam_workspace import ExamCourseCatalogResponse
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)


class GetExamCourseCatalogHandler:
    def handle(self) -> ExamCourseCatalogResponse:
        catalog = load_exam_course_catalog()
        return ExamCourseCatalogResponse(generated_at=catalog.generated_at, courses=catalog.courses)
