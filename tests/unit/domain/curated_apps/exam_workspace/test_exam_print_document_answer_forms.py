"""The print document's answer forms and their facit lines (TASK-SKRIPT-40-04-07 W3-W8)."""

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
    blank_width_mm,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    PrintBlank,
    PrintBox,
    PrintGrid,
    PrintOption,
    PrintParagraph,
    PrintParagraphStyle,
    PrintRuledLines,
    PrintText,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeGap
from tests.unit.domain.curated_apps.exam_workspace.exam_print_document_test_support import (
    all_texts,
    gap_fill_item,
    has_answer_key,
    has_blank,
    inline_choice_item,
    lone_gap_item,
    question,
    question_blocks,
    segments_paragraph,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_ordering_item,
    make_single_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)


class TestGapFill:
    def test_a_lone_gap_is_one_answer_line_with_no_blank_and_no_answer(self) -> None:
        document = make_document(lone_gap_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)
        question_entry = question(student, "item_001")

        assert question_blocks(question_entry)[1] == PrintRuledLines(count=1)
        assert not has_blank(student)
        assert "NF" not in all_texts(student)

    def test_a_lone_gap_facit_lists_the_gap(self) -> None:
        document = make_document(lone_gap_item())

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        assert question_blocks(question(facit, "item_001"))[-1] == PrintAnswerKey(
            lines=("Lucka 1: NF",)
        )

    def test_a_gap_in_a_sentence_is_a_blank_sized_for_the_longest_answer(self) -> None:
        item = gap_fill_item(
            (
                segments_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("ab", "fotosyntes")),),
        )

        student = build_print_document(make_document(item), variant=ExamPrintVariant.STUDENT)

        assert blank_width_mm(10) == 48.0
        assert PrintParagraph(
            runs=(
                PrintText("Svar: ", marks=()),
                PrintBlank(width_mm=48.0),
                PrintText(" (2 p)", marks=()),
            ),
            style=PrintParagraphStyle.GAP_LINE,
        ) in question_blocks(question(student, "item_001"))
        assert "fotosyntes" not in all_texts(student)

    def test_a_gap_in_a_sentence_facit_lists_the_accepted_values(self) -> None:
        item = gap_fill_item(
            (
                segments_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("ab", "fotosyntes")),),
        )

        facit = build_print_document(make_document(item), variant=ExamPrintVariant.FACIT)

        assert question_blocks(question(facit, "item_001"))[-1] == PrintAnswerKey(
            lines=("Lucka 1: ab / fotosyntes",)
        )


class TestInlineChoice:
    def test_an_inline_choice_gap_prints_its_option_list_between_brackets(self) -> None:
        document = make_document(inline_choice_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert PrintParagraph(
            runs=(
                PrintText("Vattnets formel är ", marks=()),
                PrintText("[H2O / CO2]", marks=()),
                PrintText(" (2 p)", marks=()),
            ),
            style=PrintParagraphStyle.BODY,
        ) in question_blocks(question(student, "item_001"))

    def test_an_inline_choice_facit_lists_the_correct_option(self) -> None:
        document = make_document(inline_choice_item())

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        assert question_blocks(question(facit, "item_001"))[-1] == PrintAnswerKey(
            lines=("Lucka 1: H2O",)
        )


class TestChoice:
    def test_single_choice_prints_tick_options_and_the_answer_only_in_facit(self) -> None:
        document = make_document(make_single_choice_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)
        question_entry = question(student, "item_001")

        assert PrintOption(
            box=PrintBox.TICK, label="A)", runs=(PrintText("vägen", marks=()),)
        ) in question_blocks(question_entry)
        assert PrintOption(
            box=PrintBox.TICK, label="B)", runs=(PrintText("eleverna", marks=()),)
        ) in question_blocks(question_entry)
        assert not has_answer_key(student)

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)
        assert question_blocks(question(facit, "item_001"))[-1] == PrintAnswerKey(
            lines=("Rätt svar: eleverna",)
        )

    def test_multiple_response_prints_tick_options(self) -> None:
        payload = make_single_choice_item().model_dump()
        payload.update(kind="multiple_response")
        document = make_document(NativeExamItem.model_validate(payload))

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert PrintOption(
            box=PrintBox.TICK, label="A)", runs=(PrintText("vägen", marks=()),)
        ) in question_blocks(question(student, "item_001"))


class TestOrdering:
    def test_numbered_steps_print_in_the_print_order(self) -> None:
        document = make_document(make_ordering_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        options = [
            block
            for block in question_blocks(question(student, "item_001"))
            if isinstance(block, PrintOption)
        ]
        assert options == [
            PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Avslutning", marks=()),)),
            PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Motargument", marks=()),)),
            PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Argument", marks=()),)),
            PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Tes", marks=()),)),
        ]

    def test_ordering_facit_lists_the_numbered_order(self) -> None:
        document = make_document(make_ordering_item())

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        assert question_blocks(question(facit, "item_001"))[-1] == PrintAnswerKey(
            lines=("Rätt ordning: Avslutning 4; Motargument 3; Argument 2; Tes 1",)
        )


class TestMatching:
    def test_matching_prints_a_grid_of_the_two_lists(self) -> None:
        document = make_document(matching_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert PrintGrid(
            rows=(
                (PrintText("hund", marks=()),),
                (PrintText("katt", marks=()),),
                (PrintText("fågel", marks=()),),
            ),
            columns=(
                (PrintText("däggdjur", marks=()),),
                (PrintText("fåglar", marks=()),),
                (PrintText("fiskar", marks=()),),
            ),
        ) in question_blocks(question(student, "item_001"))

    def test_matching_facit_lists_the_pairs(self) -> None:
        document = make_document(matching_item())

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        assert question_blocks(question(facit, "item_001"))[-1] == PrintAnswerKey(
            lines=(
                "Par: hund – däggdjur",
                "Par: katt – fåglar",
                "Par: fågel – fiskar",
            )
        )
