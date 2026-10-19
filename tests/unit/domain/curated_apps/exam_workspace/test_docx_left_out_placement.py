"""The left-out mark is decided on the placed item by anchor (TASK-SKRIPT-39-04-19).

Synthetic placement: chunks and items are built directly. An item records the anchors of
the own chunks it leaves out in ``AlignedItem.left_out``; section placement renders the
check mark only for those the placed item still does not show, neither in its body nor
on the parent that holds it.
"""

from types import MappingProxyType

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import AlignedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import LEFT_OUT_REASON
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    Placed,
    SectionInstructions,
    place_section_instructions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
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
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

pytestmark = pytest.mark.unit

_NOTHING_GOVERNED: MappingProxyType[str, frozenset[str]] = MappingProxyType({})


def _chunk(anchor: str, kind: str, text: str) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind=kind, text=text, marked_text=text)


def _item(text: str) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(
            NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
    )


def _aligned(
    item: NativeExamItem, *chunks: str | None, left_out: frozenset[str] = frozenset()
) -> AlignedItem:
    """The item with the source chunk each body paragraph shows and the anchors it leaves out."""
    return AlignedItem(item, chunks, frozenset(), left_out)


def _place(
    chunks: tuple[DocxChunk, ...],
    placed: list[Placed],
    instructions: tuple[ProducedMetadata, ...] = (),
    title_anchors: frozenset[str] = frozenset(),
    governed: MappingProxyType[str, frozenset[str]] = _NOTHING_GOVERNED,
) -> SectionInstructions:
    return place_section_instructions(
        chunks,
        placed,
        instructions,
        governed,
        title_anchors,
    )


def test_restored_heading_leaves_no_left_out_mark() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Del A"),
        _chunk("body:0003", "paragraph", "Förklara."),
    )
    ordered: list[Placed] = [
        (
            1,
            ("body:0002", "body:0003"),
            _aligned(_item("Förklara."), "body:0003", left_out=frozenset({"body:0002"})),
        )
    ]
    placed = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))

    assert placed.items[0].plain_text_lines()[0] == "Del A"
    assert placed.items[0].review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert placed.items[0].review.reasons == ()


def test_group_heading_marks_neither_child() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Del B: Cellen"),
        _chunk("body:0003", "paragraph", "Fråga ett?"),
        _chunk("body:0004", "paragraph", "Fråga två?"),
    )
    ordered: list[Placed] = [
        (
            2,
            ("body:0003",),
            _aligned(_item("Fråga ett?"), "body:0003", left_out=frozenset({"body:0002"})),
        ),
        (
            3,
            ("body:0004",),
            _aligned(_item("Fråga två?"), "body:0004", left_out=frozenset({"body:0002"})),
        ),
    ]
    placed = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))

    assert len(placed.parents) == 1
    assert body_text_lines(placed.parents[0].instruction) == ("Del B: Cellen",)
    for item in placed.items:
        assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
        assert item.review.reasons == ()


def test_unplaced_word_bank_is_marked() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "paragraph", "Första frågan?"),
        _chunk("body:0003", "paragraph", "Ord att använda: äpple och päron."),
    )
    ordered: list[Placed] = [
        (
            1,
            ("body:0002",),
            _aligned(_item("Första frågan?"), "body:0002", left_out=frozenset({"body:0003"})),
        )
    ]
    placed = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))

    assert placed.items[0].review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert placed.items[0].review.reasons == (
        LEFT_OUT_REASON,
        "Ord att använda: äpple och päron.",
    )


def test_restored_heading_with_missing_word_bank_lists_only_the_word_bank() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Del A"),
        _chunk("body:0003", "paragraph", "Förklara."),
        _chunk("body:0004", "paragraph", "Ord att använda: äpple och päron."),
    )
    ordered: list[Placed] = [
        (
            1,
            ("body:0002", "body:0003"),
            _aligned(
                _item("Förklara."),
                "body:0003",
                left_out=frozenset({"body:0002", "body:0004"}),
            ),
        )
    ]
    placed = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))

    assert placed.items[0].plain_text_lines()[0] == "Del A"
    assert placed.items[0].review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert placed.items[0].review.reasons == (
        LEFT_OUT_REASON,
        "Ord att använda: äpple och päron.",
    )


def test_unrelated_reason_stays_without_a_left_out_reason() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Del A"),
        _chunk("body:0003", "paragraph", "Förklara."),
    )
    item = _item("Förklara.").model_copy(
        update={
            "review": NativeItemReview(
                state=NativeItemReviewState.REVIEW_REQUIRED,
                parse_origin=NativeParseOrigin.LLM_PARSED,
                reasons=("Annan orsak.",),
            )
        }
    )
    ordered: list[Placed] = [
        (
            1,
            ("body:0002", "body:0003"),
            _aligned(item, "body:0003", left_out=frozenset({"body:0002"})),
        )
    ]
    placed = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))

    assert placed.items[0].review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert placed.items[0].review.reasons == ("Annan orsak.",)


def test_repeated_placement_marks_a_missing_chunk_once() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "paragraph", "Första frågan?"),
        _chunk("body:0003", "paragraph", "Ord att använda: äpple och päron."),
    )
    ordered: list[Placed] = [
        (
            1,
            ("body:0002",),
            _aligned(_item("Första frågan?"), "body:0002", left_out=frozenset({"body:0003"})),
        )
    ]
    first = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))
    second = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))

    assert (
        first.items[0].review.reasons
        == second.items[0].review.reasons
        == (
            LEFT_OUT_REASON,
            "Ord att använda: äpple och päron.",
        )
    )
    assert ordered[0][2].item.review.reasons == ()


def test_source_item_with_left_out_stays_unchanged() -> None:
    chunks = (
        _chunk("body:0001", "heading", "Provets titel"),
        _chunk("body:0002", "heading", "Del A"),
        _chunk("body:0003", "paragraph", "Förklara."),
    )
    item = _item("Förklara.").model_copy(
        update={
            "review": NativeItemReview(
                state=NativeItemReviewState.REVIEW_COMPLETE,
                parse_origin=NativeParseOrigin.SOURCE_FALLBACK,
            )
        }
    )
    before = item.review
    ordered: list[Placed] = [
        (
            1,
            ("body:0002", "body:0003"),
            _aligned(item, "body:0003", left_out=frozenset({"body:0002"})),
        )
    ]
    placed = _place(chunks, ordered, title_anchors=frozenset({"body:0001"}))

    assert placed.items[0].review == before
