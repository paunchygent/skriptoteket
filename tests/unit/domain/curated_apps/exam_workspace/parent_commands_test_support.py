"""Shared documents and structure checks for the native parent command tests."""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
)


def _exam() -> NativeExamDocument:
    # Keep a converted mixed-kind parent in place while authoring another parent.
    return recorded_document((parent_over("parent_001", "Existing instruction", 2, 3),))


def _saved_exam(*, single_child: bool = False) -> NativeExamDocument:
    # Recorded conversion items, with explicit test grouping, reopened from the saved JSON shape.
    document = recorded_document(
        (
            parent_over("parent_001", "First instruction", *((2,) if single_child else (2, 3, 4))),
            parent_over("parent_002", "Untouched instruction", 6, 7),
        )
    )
    return parse_native_exam_document(native_exam_document_json_bytes(document))


def _check_structure(document: NativeExamDocument) -> None:
    # Re-enter full validation: model_copy alone does not establish the invariants.
    NativeExamDocument.model_validate(document.model_dump())
    assert [item.sequence for item in document.items] == list(range(1, len(document.items) + 1))
