"""Print layout decisions for printed exams (TASK-SKRIPT-40-04-07 W6-W8)."""

from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    TEXT_WIDTH_MM,
    blank_width_mm,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_layout import (
    GapPrintForm,
    ParagraphPrintRole,
    is_answer_line_paragraph,
    item_print_layout,
    paragraph_print_role,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_ordering_item,
    make_paragraph,
    make_review,
    make_single_choice_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)

ASSET_ID = "asset_0123456789abcdef"


def gap_paragraph(
    *segments: NativeTextSegment | NativeGapSegment | NativeAssetSegment,
) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=segments)


def gap_fill_item(
    body: tuple[NativeParagraph, ...],
    gaps: tuple[NativeGap, ...],
    *,
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=body,
        points=2,
        gaps=gaps,
        answer_key=NativeAnswerKey(origin=origin),
        review=make_review(),
    )


def inline_choice_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.INLINE_CHOICE,
        body=(
            gap_paragraph(
                NativeTextSegment(text="Vattnets formel är ", marks=()),
                NativeGapSegment(gap_id="gap_001"),
            ),
        ),
        points=2,
        gaps=(
            NativeGap(
                gap_id="gap_001",
                options=(
                    NativeChoice(choice_id="choice_001", body=plain_body("H2O")),
                    NativeChoice(choice_id="choice_002", body=plain_body("CO2")),
                ),
                correct_option_id="choice_001",
            ),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=make_review(),
    )


def multiple_response_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.MULTIPLE_RESPONSE,
        body=(make_paragraph("Vilka stämmer?"),),
        points=2,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("a")),
            NativeChoice(choice_id="choice_002", body=plain_body("b")),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            correct_choice_ids=("choice_001",),
        ),
        review=make_review(),
    )


class TestIsAnswerLineParagraph:
    def test_a_lone_gap_is_an_answer_line(self) -> None:
        paragraph = gap_paragraph(NativeGapSegment(gap_id="gap_001"))

        assert is_answer_line_paragraph(paragraph) is True

    def test_whitespace_only_text_around_a_gap_keeps_it_an_answer_line(self) -> None:
        paragraph = gap_paragraph(
            NativeTextSegment(text="   ", marks=()),
            NativeGapSegment(gap_id="gap_001"),
            NativeTextSegment(text="  ", marks=()),
        )

        assert is_answer_line_paragraph(paragraph) is True

    def test_a_gap_after_wording_is_not_an_answer_line(self) -> None:
        paragraph = gap_paragraph(
            NativeTextSegment(text="Svar: ", marks=()),
            NativeGapSegment(gap_id="gap_001"),
        )

        assert is_answer_line_paragraph(paragraph) is False

    def test_two_gaps_in_one_paragraph_are_not_an_answer_line(self) -> None:
        paragraph = gap_paragraph(
            NativeGapSegment(gap_id="gap_001"),
            NativeGapSegment(gap_id="gap_002"),
        )

        assert is_answer_line_paragraph(paragraph) is False

    def test_a_picture_next_to_a_gap_is_not_an_answer_line(self) -> None:
        paragraph = gap_paragraph(
            NativeAssetSegment(asset_id=ASSET_ID),
            NativeGapSegment(gap_id="gap_001"),
        )

        assert is_answer_line_paragraph(paragraph) is False

    def test_a_text_only_paragraph_is_not_an_answer_line(self) -> None:
        assert is_answer_line_paragraph(make_paragraph("Bara text.")) is False


class TestParagraphPrintRole:
    def test_a_kind_other_than_gap_fill_has_text_paragraphs_only(self) -> None:
        item = inline_choice_item()

        assert paragraph_print_role(item, item.body[0]) is ParagraphPrintRole.TEXT

    def test_a_lone_gap_prints_as_an_answer_line(self) -> None:
        item = gap_fill_item(
            (gap_paragraph(NativeGapSegment(gap_id="gap_001")),),
            (NativeGap(gap_id="gap_001", accepted_values=("NF",)),),
        )

        assert paragraph_print_role(item, item.body[0]) is ParagraphPrintRole.ANSWER_LINE

    def test_a_gap_inside_a_sentence_prints_as_a_gap_line(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("NF",)),),
        )

        assert paragraph_print_role(item, item.body[0]) is ParagraphPrintRole.GAP_LINE

    def test_two_gaps_in_one_paragraph_print_as_a_gap_line(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeGapSegment(gap_id="gap_001"),
                    NativeGapSegment(gap_id="gap_002"),
                ),
            ),
            (
                NativeGap(gap_id="gap_001", accepted_values=("a",)),
                NativeGap(gap_id="gap_002", accepted_values=("b",)),
            ),
        )

        assert paragraph_print_role(item, item.body[0]) is ParagraphPrintRole.GAP_LINE


class TestItemPrintLayout:
    def test_a_lone_gap_is_a_full_width_answer_line(self) -> None:
        item = gap_fill_item(
            (gap_paragraph(NativeGapSegment(gap_id="gap_001")),),
            (NativeGap(gap_id="gap_001", accepted_values=("NF",)),),
        )

        layout = item_print_layout(item)

        assert layout.gap_forms["gap_001"] == GapPrintForm(
            gap_id="gap_001", answer_line=True, width_mm=TEXT_WIDTH_MM
        )

    def test_whitespace_around_a_lone_gap_still_makes_an_answer_line(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeTextSegment(text="  ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("NF",)),),
        )

        layout = item_print_layout(item)

        assert layout.gap_forms["gap_001"].answer_line is True
        assert layout.gap_forms["gap_001"].width_mm == TEXT_WIDTH_MM

    def test_a_gap_inside_a_sentence_uses_the_sized_blank(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("ab", "fotosyntes")),),
        )

        layout = item_print_layout(item)

        assert layout.gap_forms["gap_001"].answer_line is False
        assert layout.gap_forms["gap_001"].width_mm == blank_width_mm(10)
        assert layout.gap_forms["gap_001"].width_mm == 48.0

    def test_two_gaps_in_one_paragraph_both_get_inline_forms(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text=" eller ", marks=()),
                    NativeGapSegment(gap_id="gap_002"),
                ),
            ),
            (
                NativeGap(gap_id="gap_001", accepted_values=("a",)),
                NativeGap(gap_id="gap_002", accepted_values=("b",)),
            ),
        )

        layout = item_print_layout(item)

        assert set(layout.gap_forms) == {"gap_001", "gap_002"}
        assert all(form.answer_line is False for form in layout.gap_forms.values())

    def test_a_picture_next_to_a_gap_keeps_the_gap_inline(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeAssetSegment(asset_id=ASSET_ID),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("x",)),),
        )

        layout = item_print_layout(item)

        assert layout.gap_forms["gap_001"].answer_line is False

    def test_a_gap_without_accepted_values_uses_the_minimum_width(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001"),),
            origin=NativeAnswerKeyOrigin.ABSENT,
        )

        layout = item_print_layout(item)

        assert layout.gap_forms["gap_001"].width_mm == 30.0

    def test_a_longer_accepted_value_widens_the_blank(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("ab", "fotosyntes")),),
        )

        assert item_print_layout(item).gap_forms["gap_001"].width_mm == 48.0

    def test_a_very_long_answer_caps_at_the_text_width(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("x" * 60,)),),
        )

        assert item_print_layout(item).gap_forms["gap_001"].width_mm == TEXT_WIDTH_MM

    def test_surrounding_spaces_in_an_accepted_value_do_not_count(self) -> None:
        item = gap_fill_item(
            (
                gap_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("   fotosyntes   ",)),),
        )

        assert item_print_layout(item).gap_forms["gap_001"].width_mm == 48.0

    def test_gap_forms_are_an_immutable_mapping(self) -> None:
        item = gap_fill_item(
            (gap_paragraph(NativeGapSegment(gap_id="gap_001")),),
            (NativeGap(gap_id="gap_001", accepted_values=("NF",)),),
        )

        assert isinstance(item_print_layout(item).gap_forms, MappingProxyType)

    def test_an_inline_choice_item_has_no_gap_forms(self) -> None:
        item = inline_choice_item()

        layout = item_print_layout(item)

        assert layout.gap_forms == {}
        assert layout.writing_lines == 0
        assert layout.tick_boxes is False
        assert paragraph_print_role(item, item.body[0]) is ParagraphPrintRole.TEXT

    def test_free_text_prints_its_writing_lines(self) -> None:
        item = NativeExamItem.model_validate(
            {**make_free_text_item().model_dump(), "writing_lines": 12}
        )

        layout = item_print_layout(item)

        assert layout.writing_lines == 12
        assert layout.tick_boxes is False
        assert layout.gap_forms == {}

    def test_single_choice_gets_tick_boxes(self) -> None:
        layout = item_print_layout(make_single_choice_item())

        assert layout.tick_boxes is True
        assert layout.writing_lines == 0

    def test_multiple_response_gets_tick_boxes(self) -> None:
        layout = item_print_layout(multiple_response_item())

        assert layout.tick_boxes is True
        assert layout.writing_lines == 0

    def test_matching_keeps_its_own_boxes(self) -> None:
        layout = item_print_layout(matching_item())

        assert layout.tick_boxes is False
        assert layout.writing_lines == 0

    def test_ordering_keeps_its_own_boxes(self) -> None:
        layout = item_print_layout(make_ordering_item())

        assert layout.tick_boxes is False
        assert layout.writing_lines == 0
