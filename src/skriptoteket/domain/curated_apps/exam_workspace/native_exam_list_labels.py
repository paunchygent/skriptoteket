"""Workspace list labels for native exam questions (user rule 2026-10-19).

Domain purpose:
    The display number of every question in document order: each standalone
    question and each part with children takes the next number once; a part's
    children follow as "<number><letter>" and take no number of their own.
    A part with no questions takes no number. The one backend twin of the
    frontend ``examWorkspaceListEntries.ts`` unit labels, so server copy that
    names a question reads exactly as the list rows and the editor headings
    ("Fråga 2", "1b").

Relationships:
    - Pure; consumed by the exam workspace export renderer for blocker copy.
    - Reads the one document order from ``native_exam_outline.document_outline``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_outline import (
    OutlinePart,
    OutlineQuestion,
    document_outline,
)

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
        NativeExamDocument,
    )

_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _child_letter(index: int) -> str:
    """The child suffix: a-z, then aa, ab, matching the frontend list entries."""
    if index < len(_LETTERS):
        return _LETTERS[index]
    return f"{_LETTERS[index // len(_LETTERS) - 1]}{_LETTERS[index % len(_LETTERS)]}"


def native_exam_question_labels(document: NativeExamDocument) -> dict[str, str]:
    """The question list's label per item id: a standalone "3", a child "3b"."""
    labels: dict[str, str] = {}
    number = 0
    for entry in document_outline(document):
        if isinstance(entry, OutlineQuestion):
            number += 1
            labels[entry.item.item_id] = str(number)
            continue
        if isinstance(entry, OutlinePart):
            if not entry.children:
                continue
            number += 1
            for child_index, child in enumerate(entry.children):
                labels[child.item_id] = f"{number}{_child_letter(child_index)}"
    return labels
