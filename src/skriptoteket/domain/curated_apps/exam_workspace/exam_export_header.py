"""Generated printable exam header shared by the native PDF and DOCX exports."""

from decimal import Decimal

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)


def exam_export_header_lines(document: NativeExamDocument) -> tuple[str, ...]:
    """Use item points, never the source's printed total, for the generated total."""
    lines = [document.title]
    if document.header.course_hint is not None:
        lines.append(document.header.course_hint)
    points = [Decimal(str(item.points)) for item in document.items if item.points is not None]
    if points:
        total = format(sum(points, start=Decimal(0)), "f")
        if "." in total:
            total = total.rstrip("0").rstrip(".")
        lines.append(f"Totalt: {total.replace('.', ',')} poäng")
    return tuple(lines)
