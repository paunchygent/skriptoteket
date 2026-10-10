"""Shared test helpers for building native exam document inputs."""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)


def with_next_revision(document: NativeExamDocument) -> NativeExamDocument:
    """Return the document with its revision advanced by exactly one."""
    return document.model_copy(update={"revision": document.revision + 1})
