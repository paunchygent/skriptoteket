"""Review bodies show the source word without its inline answer key (TASK-SKRIPT-39-04-17).

When ``gap_count_mismatch`` sends an item to review, each body paragraph is cut
from its inline answer label onward, with the wrapper ``(`` rule. A picture
after the cut stays, after the kept text. A paragraph the cut leaves empty is
removed together with its aligned chunk entry.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    AlignedItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextMark,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.review_answer_key_cut import (
    without_inline_answer_keys,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_plain_text,
)

pytestmark = pytest.mark.unit

_PICTURE = "asset_0123456789abcdef"


def _text(text: str, marks: tuple[NativeTextMark, ...] = ()) -> NativeTextSegment:
    return NativeTextSegment(text=text, marks=marks)


def _aligned(
    *paragraphs: NativeParagraph,
    kind: NativeExamItemKind = NativeExamItemKind.FREE_TEXT,
) -> AlignedItem:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=kind,
        body=paragraphs,
        gaps=((NativeGap(gap_id="gap_001"),) if kind is NativeExamItemKind.GAP_FILL else ()),
        answer_key=NativeAnswerKey(
            origin=(
                NativeAnswerKeyOrigin.NOT_APPLICABLE
                if kind is NativeExamItemKind.FREE_TEXT
                else NativeAnswerKeyOrigin.ABSENT
            )
        ),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.SOURCE_FALLBACK,
        ),
    )
    return AlignedItem(
        item,
        tuple(f"body:{index:04d}" for index in range(1, len(paragraphs) + 1)),
        frozenset({"body:0001"}),
    )


def test_a_body_paragraph_is_cut_from_its_inline_answer_label_onward():
    aligned = _aligned(
        NativeParagraph(
            heading_level=None, segments=(_text("a) snöbollarnas Svar: snö (R) + boll (R)"),)
        )
    )

    result = without_inline_answer_keys(aligned)

    assert body_plain_text(result.item.body) == "a) snöbollarnas"
    assert result.entry_chunks == frozenset({"body:0001"})


def test_a_wrapped_answer_label_cuts_the_review_body_at_the_wrapper():
    aligned = _aligned(
        NativeParagraph(heading_level=None, segments=(_text("a) solrosornas (Svar: sol)"),))
    )

    result = without_inline_answer_keys(aligned)

    assert body_plain_text(result.item.body) == "a) solrosornas"


def test_a_paragraph_without_a_label_is_unchanged_including_its_marks():
    paragraph = NativeParagraph(
        heading_level=None,
        segments=(_text("a) ordet", ("italic",)), _text(" utan nyckel")),
    )
    aligned = _aligned(paragraph)

    result = without_inline_answer_keys(aligned)

    assert result.item.body == (paragraph,)
    assert result.chunks == aligned.chunks


def test_a_paragraph_holding_only_the_answer_key_leaves_with_its_chunk_entry():
    kept = NativeParagraph(heading_level=None, segments=(_text("b) ordet"),))
    aligned = _aligned(
        NativeParagraph(heading_level=None, segments=(_text("Svar: ________"),)),
        kept,
    )

    result = without_inline_answer_keys(aligned)

    assert result.item.body == (kept,)
    assert result.chunks == ("body:0002",)
    assert len(result.item.body) == len(result.chunks)


def test_a_picture_after_the_label_stays_after_the_kept_text():
    aligned = _aligned(
        NativeParagraph(
            heading_level=None,
            segments=(
                _text("a) ordet Svar: nyckeln"),
                NativeAssetSegment(asset_id=_PICTURE),
                NativeGapSegment(gap_id="gap_001"),
            ),
        ),
        kind=NativeExamItemKind.GAP_FILL,
    )

    result = without_inline_answer_keys(aligned)

    (paragraph,) = result.item.body
    assert (
        "".join(
            segment.text for segment in paragraph.segments if isinstance(segment, NativeTextSegment)
        )
        == "a) ordet"
    )
    assert paragraph.segments[-2:] == (
        NativeAssetSegment(asset_id=_PICTURE),
        NativeGapSegment(gap_id="gap_001"),
    )


def test_an_italic_segment_before_the_label_keeps_its_mark():
    aligned = _aligned(
        NativeParagraph(
            heading_level=None,
            segments=(_text("a) snöbollarnas ", ("italic",)), _text("Svar: snö")),
        )
    )

    result = without_inline_answer_keys(aligned)

    (paragraph,) = result.item.body
    (segment,) = paragraph.segments
    assert isinstance(segment, NativeTextSegment)
    assert segment.text == "a) snöbollarnas"
    assert segment.marks == ("italic",)
