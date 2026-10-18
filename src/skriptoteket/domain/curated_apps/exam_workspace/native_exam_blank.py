"""The blank exam a guest starts from (TASK-SKRIPT-41-02-02).

Purpose:
    Build the one valid empty document the public workspace blank route returns:
    no title, no course, revision 1 like a fresh import, and exactly one empty
    question of the editor's first "Ny uppgift" menu kind (Fritext).

Relationships:
    - Pure domain construction over ``NativeExamDocument``; no IO and no state.
    - The guest editor keeps the result in the browser; nothing server-side stores it.
"""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

BLANK_EXAM_REVISION = 1
BLANK_EXAM_ITEM_ID = "item_001"
BLANK_EXAM_POINTS = 1


def blank_native_exam_item(*, sequence: int = 1) -> NativeExamItem:
    """The server-side shape of the editor's first new-question kind, empty and worth one point."""
    return NativeExamItem(
        item_id=BLANK_EXAM_ITEM_ID,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(),
        points=BLANK_EXAM_POINTS,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.TEACHER_CREATED,
        ),
    )


def blank_native_exam_document() -> NativeExamDocument:
    """A valid empty exam: empty title, no course, revision 1, one empty question."""
    return NativeExamDocument(
        document_id=uuid4(),
        revision=BLANK_EXAM_REVISION,
        title="",
        items=(blank_native_exam_item(),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
