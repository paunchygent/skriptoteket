"""Which items block a native exam document's export, and which hold a trusted answer key.

Export needs every value the export carries, never a parsing doubt (TASK-SKRIPT-39-05-07 D1).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

_TRUSTED_KEY_ORIGINS = frozenset(
    {
        NativeAnswerKeyOrigin.SOURCE_PROVIDED,
        NativeAnswerKeyOrigin.AI_INTERPRETED,
        NativeAnswerKeyOrigin.TEACHER_AUTHORED,
        NativeAnswerKeyOrigin.REVIEWED_ADVISORY,
    }
)

_KEYED_KINDS = frozenset(
    {
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.MULTIPLE_RESPONSE,
        NativeExamItemKind.GAP_FILL,
        NativeExamItemKind.MATCHING,
    }
)


class NativeExportBlocker(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    item_id: str
    reason: Literal[
        "unbuilt_question",
        "machine_proposed_key_unreviewed",
        "missing_points",
        "missing_answer_key",
    ]


def native_export_blockers(document: NativeExamDocument) -> tuple[NativeExportBlocker, ...]:
    """S4 gate: export needs every value the export carries, never a parsing doubt (D1).

    An unbuilt question, printed from source because the import could not convert it, blocks
    until the teacher marks it reviewed (D2). A named source-picture loss also blocks;
    other converted items that need review do not block.
    Keyed kinds without an answer key block export: Exam.net QTI would carry an
    automatic item with no correct response and the Exam.net PDF prints the key.
    """
    blockers: list[NativeExportBlocker] = []
    for item in document.items:
        if is_unbuilt_question(item):
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="unbuilt_question"))
        if item.answer_key.origin is NativeAnswerKeyOrigin.MACHINE_PROPOSED:
            blockers.append(
                NativeExportBlocker(
                    item_id=item.item_id,
                    reason="machine_proposed_key_unreviewed",
                )
            )
        if item.kind in _KEYED_KINDS and item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT:
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="missing_answer_key"))
        if item.points is None:
            blockers.append(NativeExportBlocker(item_id=item.item_id, reason="missing_points"))
    return tuple(blockers)


def is_unbuilt_question(item: NativeExamItem) -> bool:
    """An unfinished source question, including a named picture loss, pending teacher review."""
    missing_picture = item.retry_source is not None and item.retry_source.has_missing_pictures()
    return item.review.state is NativeItemReviewState.REVIEW_REQUIRED and (
        item.review.parse_origin is NativeParseOrigin.DETERMINISTIC or missing_picture
    )


def item_has_trusted_key(item: NativeExamItem) -> bool:
    if item.kind not in _KEYED_KINDS:
        return False
    return item.answer_key.origin in _TRUSTED_KEY_ORIGINS
