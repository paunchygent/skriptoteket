"""Readable native exam text for document-wide language inference."""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines


def native_exam_document_text(document: NativeExamDocument) -> str:
    """Read the whole exam, without automatic spellings or editor-owned labels."""
    lines = [document.title, *body_text_lines(document.instructions)]
    for parent in document.parents:
        lines.extend(body_text_lines(parent.instruction))
    for item in document.items:
        lines.extend(text for text in (item.printed_label, item.facit_text) if text)
        lines.extend(body_text_lines(item.body))
        lines.extend(line for choice in item.choices for line in body_text_lines(choice.body))
        lines.extend(line for entry in item.match_left for line in body_text_lines(entry.body))
        lines.extend(line for entry in item.match_right for line in body_text_lines(entry.body))
    return "\n".join(line.strip() for line in lines if line.strip())
