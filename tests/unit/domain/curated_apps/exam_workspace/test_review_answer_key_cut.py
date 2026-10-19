"""Review bodies show the source word without its inline answer key (TASK-SKRIPT-39-04-17).

When ``gap_count_mismatch`` sends an item to review, each body paragraph is cut
from its inline answer label onward, with the wrapper ``(`` rule. A picture
after the cut stays, after the kept text. A paragraph the cut leaves empty is
removed together with its aligned chunk entry.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
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
from skriptoteket.domain.curated_apps.exam_workspace.source_answer_space import (
    is_answer_line_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    ANSWER_LABEL,
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
        writing_lines=DEFAULT_WRITING_LINES if kind is NativeExamItemKind.FREE_TEXT else None,
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


def _carried_key_lines(result: AlignedItem) -> list[str]:
    assert result.item.facit_text is not None
    return result.item.facit_text.split("\n")


def test_cut_paragraphs_carry_their_key_lines_in_body_order_with_prefixes():
    aligned = _aligned(
        NativeParagraph(
            heading_level=None, segments=(_text("a) snöbollarnas Svar: snö (R) + boll (R)"),)
        ),
        NativeParagraph(
            heading_level=None, segments=(_text("b) skrivbarheten Svar: skriv (R) + bar (A)"),)
        ),
        NativeParagraph(
            heading_level=None, segments=(_text("c) fotbollsspelarnas Svar: fot (R) + boll (R)"),)
        ),
    )

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text == (
        "a) Svar: snö (R) + boll (R)\nb) Svar: skriv (R) + bar (A)\nc) Svar: fot (R) + boll (R)"
    )
    assert body_plain_text(result.item.body) == (
        "a) snöbollarnas\nb) skrivbarheten\nc) fotbollsspelarnas"
    )
    assert result.item.answer_key.origin is NativeAnswerKeyOrigin.NOT_APPLICABLE
    assert result.item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert result.item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK


def test_a_paragraph_without_a_list_label_carries_a_line_from_the_label():
    aligned = _aligned(
        NativeParagraph(heading_level=None, segments=(_text("Ordet snö Svar: snö (R)"),))
    )

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text == "Svar: snö (R)"
    assert body_plain_text(result.item.body) == "Ordet snö"


def test_a_wrapped_answer_label_carries_the_wrapper_line_with_its_prefix():
    aligned = _aligned(NativeParagraph(heading_level=None, segments=(_text("a) ord (Svar: x)"),)))

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text == "a) (Svar: x)"
    assert body_plain_text(result.item.body) == "a) ord"


@pytest.mark.parametrize(
    "tail",
    ["Svar:", "Svar:   ", "Svar: ______", "Svar: _", "Svar: [ ]", "(Svar: ____)"],
)
def test_a_printed_answer_line_carries_nothing_and_leaves_facit_unset(tail: str):
    aligned = _aligned(NativeParagraph(heading_level=None, segments=(_text(tail),)))

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text is None
    assert result.item.answer_key.origin is NativeAnswerKeyOrigin.NOT_APPLICABLE


def test_trailing_spaces_in_the_key_are_trimmed():
    aligned = _aligned(NativeParagraph(heading_level=None, segments=(_text("a) ord Svar: x   "),)))

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text == "a) Svar: x"


def test_a_picture_after_the_cut_stays_in_the_body_and_out_of_the_key():
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

    assert result.item.facit_text == "a) Svar: nyckeln"
    (paragraph,) = result.item.body
    assert paragraph.segments[-2:] == (
        NativeAssetSegment(asset_id=_PICTURE),
        NativeGapSegment(gap_id="gap_001"),
    )


def test_a_paragraph_without_an_answer_label_adds_no_line():
    aligned = _aligned(
        NativeParagraph(heading_level=None, segments=(_text("Ordet snö utan nyckel"),))
    )

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text is None
    assert body_plain_text(result.item.body) == "Ordet snö utan nyckel"


def test_a_mixed_body_keeps_line_order():
    aligned = _aligned(
        NativeParagraph(heading_level=None, segments=(_text("Ordet snö Svar: x"),)),
        NativeParagraph(heading_level=None, segments=(_text("b) ord Svar: y"),)),
    )

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text == "Svar: x\nb) Svar: y"


def test_a_key_split_over_segments_with_marks_is_joined_verbatim():
    aligned = _aligned(
        NativeParagraph(
            heading_level=None,
            segments=(
                _text("a) snöbollarnas Svar: "),
                _text("snö (R) + boll (R) + ar (B) + na (B) + s (B)", ("italic",)),
            ),
        )
    )

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text == "a) Svar: snö (R) + boll (R) + ar (B) + na (B) + s (B)"
    assert body_plain_text(result.item.body) == "a) snöbollarnas"


def test_the_body_never_holds_the_label_or_the_key():
    aligned = _aligned(
        NativeParagraph(
            heading_level=None, segments=(_text("a) snöbollarnas Svar: snö (R) + boll (R)"),)
        ),
        NativeParagraph(
            heading_level=None, segments=(_text("b) skrivbarheten Svar: skriv (R) + bar (A)"),)
        ),
    )

    result = without_inline_answer_keys(aligned)

    text = body_plain_text(result.item.body)
    assert "Svar:" not in text
    assert "snö (R)" not in text
    assert "skriv (R)" not in text


def test_every_carried_line_holds_a_real_key_after_its_label():
    aligned = _aligned(
        NativeParagraph(
            heading_level=None, segments=(_text("a) snöbollarnas Svar: snö (R) + boll (R)"),)
        ),
        NativeParagraph(heading_level=None, segments=(_text("Ordet snö Svar: x"),)),
        NativeParagraph(heading_level=None, segments=(_text("c) ord (Svar: y)"),)),
    )

    result = without_inline_answer_keys(aligned)

    for line in _carried_key_lines(result):
        label = ANSWER_LABEL.search(line)
        assert label is not None
        assert not is_answer_line_text(line[label.end() :])


@pytest.mark.parametrize(
    ("body", "kept"),
    [("question text Svar: x", "question text"), ("QUESTION text Svar: x", "QUESTION text")],
)
def test_an_unlabelled_word_carries_the_key_without_a_prefix(body: str, kept: str):
    """Unlabelled ordinary words carry the key line with no label prefix (F1)."""
    aligned = _aligned(NativeParagraph(heading_level=None, segments=(_text(body),)))

    result = without_inline_answer_keys(aligned)

    assert result.item.facit_text == "Svar: x"
    assert body_plain_text(result.item.body) == kept
