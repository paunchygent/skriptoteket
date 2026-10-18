"""Reusable builders for native exam document unit tests."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
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
    return NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),))


def plain_body(text: str) -> tuple[NativeParagraph, ...]:
    """One explicitly unformatted paragraph: a plain test source, never a formatted one."""
    return (make_paragraph(text),)


def make_free_text_item(*, sequence: int = 1, item_id: str = "item_001") -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(make_paragraph("Resonera om renässansen."),),
        points=4,
        writing_lines=DEFAULT_WRITING_LINES,
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
            NativeChoice(choice_id="choice_001", body=plain_body("vägen")),
            NativeChoice(choice_id="choice_002", body=plain_body("eleverna")),
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
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Ange frastyp: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
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


ORDERING_STEPS = ("Tes", "Argument", "Motargument", "Avslutning")


def make_ordering_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    steps: tuple[str, ...] = ORDERING_STEPS,
    print_order: tuple[str, ...] | None = None,
    points: int | float | None = 1,
) -> NativeExamItem:
    """Steps in key order; the print order defaults to the key order reversed."""
    choice_ids = tuple(f"choice_{index:03d}" for index in range(1, len(steps) + 1))
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.ORDERING,
        body=(make_paragraph("Sätt stegen i en argumenterande text i rätt ordning."),),
        points=points,
        choices=tuple(
            NativeChoice(choice_id=choice_id, body=plain_body(text))
            for choice_id, text in zip(choice_ids, steps, strict=True)
        ),
        print_order=print_order if print_order is not None else tuple(reversed(choice_ids)),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED),
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
