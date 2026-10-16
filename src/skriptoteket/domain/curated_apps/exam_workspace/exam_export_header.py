"""Generated printable exam header shared by the native PDF and DOCX exports."""

from decimal import Decimal

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamHeader,
)


def exam_course_line(header: NativeExamHeader) -> str | None:
    """Prefer the chosen official course name over the source's raw hint."""
    return header.course.name if header.course is not None else header.course_hint


def exam_export_header_lines(document: NativeExamDocument) -> tuple[str, ...]:
    """Use item points, never the source's printed total, for the generated total."""
    lines = [document.title]
    course = exam_course_line(document.header)
    if course is not None:
        lines.append(course)
    points = [Decimal(str(item.points)) for item in document.items if item.points is not None]
    if points:
        total = format(sum(points, start=Decimal(0)), "f")
        if "." in total:
            total = total.rstrip("0").rstrip(".")
        lines.append(f"Totalt: {total.replace('.', ',')} poäng")
    return tuple(lines)
