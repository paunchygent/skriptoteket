"""Typed helpers shared by the conversion-merge test modules."""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)


def _teacher_save(document: NativeExamDocument, **changes: object) -> NativeExamDocument:
    return NativeExamDocument.model_validate(
        document.model_copy(update={"revision": document.revision + 1, **changes}).model_dump()
    )


def _texts(document: NativeExamDocument) -> list[str]:
    return [
        "".join(s.text for s in item.body[0].segments if isinstance(s, NativeTextSegment))
        for item in document.items
    ]
