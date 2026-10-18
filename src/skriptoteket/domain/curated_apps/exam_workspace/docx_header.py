"""Read source header metadata without admitting header lines as exam text."""

from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    manifest_questions,
    printed_points_plan,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    ExamCourse,
    match_course_hint,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamDocument,
    NativeExamHeader,
)


@dataclass(frozen=True)
class HeaderApplication:
    document: NativeExamDocument


def resolve_header_course(
    course_hint: str, course_key: str | None, courses: tuple[ExamCourse, ...]
) -> ExamCourseChoice | None:
    if course_key is not None:
        chosen = next((entry for entry in courses if entry.key == course_key), None)
        if chosen is None:
            raise ValueError(f"Unknown exam course key: {course_key}")
    else:
        match = match_course_hint(course_hint, courses)
        chosen = match.course if match.kind == "unique" else None
    return ExamCourseChoice(key=chosen.key, name=chosen.name) if chosen else None


def apply_header(
    document: NativeExamDocument,
    manifest: ExamManifest | None,
    chunks: tuple[DocxChunk, ...],
    *,
    course_key: str | None,
    courses: tuple[ExamCourse, ...],
) -> HeaderApplication:
    """Attach the source course and the exam total its total lines print (D3).

    Part and question totals score the items during assembly (``apply_printed_points``).
    """
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    headers = sorted(manifest.header, key=lambda entry: positions[entry.anchor]) if manifest else []
    course_hint = " ".join(
        text for h in headers if h.kind == "course" if (text := by_anchor[h.anchor].text.strip())
    )
    course = resolve_header_course(course_hint, course_key, courses)
    total = (
        printed_points_plan(chunks, manifest_questions(manifest)).exam_total
        if manifest is not None
        else None
    )
    return HeaderApplication(
        document.model_copy(
            update={
                "header": NativeExamHeader(
                    course=course, course_hint=course_hint or None, printed_total=total
                ),
            }
        ),
    )
