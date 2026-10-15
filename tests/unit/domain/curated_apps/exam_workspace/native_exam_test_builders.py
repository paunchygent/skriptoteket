"""Reusable builders for native exam document unit tests."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)


def make_review(
    *,
    state: NativeItemReviewState = NativeItemReviewState.REVIEW_COMPLETE,
    parse_origin: NativeParseOrigin = NativeParseOrigin.DETERMINISTIC,
    confidence: float | None = 0.9,
) -> NativeItemReview:
    return NativeItemReview(state=state, parse_origin=parse_origin, confidence=confidence)


def make_paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(segments=(NativeTextSegment(text=text),))


def make_free_text_item(*, sequence: int = 1, item_id: str = "item_001") -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(make_paragraph("Resonera om renässansen."),),
        points=4,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=make_review(),
    )


def make_single_choice_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
    correct: tuple[str, ...] = ("choice_002",),
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(make_paragraph("Vilket är huvudordet?"),),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", text="vägen"),
            NativeChoice(choice_id="choice_002", text="eleverna"),
        ),
        answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=correct),
        review=make_review(),
    )


def make_gap_fill_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    accepted: tuple[str, ...] = ("NF",),
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
    automatic: tuple[str, ...] = (),
    facit_text: str | None = None,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        facit_text=facit_text,
        body=(
            NativeParagraph(
                segments=(
                    NativeTextSegment(text="Ange frastyp: "),
                    NativeGapSegment(gap_id="gap_001"),
                )
            ),
        ),
        points=2,
        gaps=(
            NativeGap(
                gap_id="gap_001",
                accepted_values=accepted,
                automatic_values=automatic,
            ),
        ),
        answer_key=NativeAnswerKey(origin=origin),
        review=make_review(),
    )


def make_document(*items: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=tuple(items),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
