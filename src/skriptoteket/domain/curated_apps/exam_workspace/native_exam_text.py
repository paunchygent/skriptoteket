"""Readable native exam text for document-wide language inference."""

from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)


def _paragraphs(paragraphs: Iterable[NativeParagraph]) -> list[str]:
    return [
        " ".join(segment.text for segment in paragraph.segments if segment.kind == "text")
        for paragraph in paragraphs
    ]


def native_exam_document_text(document: NativeExamDocument) -> str:
    """Read the whole exam, without automatic spellings or editor-owned labels."""
    lines = [document.title, *_paragraphs(document.instructions)]
    for parent in document.parents:
        lines.extend(_paragraphs(parent.instruction))
    for item in document.items:
        lines.extend(text for text in (item.printed_label, item.facit_text) if text)
        lines.extend(_paragraphs(item.body))
        lines.extend(choice.text for choice in item.choices)
        lines.extend(entry.text for entry in item.match_left)
        lines.extend(entry.text for entry in item.match_right)
    return "\n".join(line.strip() for line in lines if line.strip())
