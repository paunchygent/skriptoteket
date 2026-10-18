"""The format-neutral print document, student and facit (TASK-SKRIPT-40-04-07 W1-W9)."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
    blank_width_mm,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    PrintBlank,
    PrintBlock,
    PrintBox,
    PrintDocument,
    PrintGrid,
    PrintHeading,
    PrintImage,
    PrintInstruction,
    PrintOption,
    PrintParagraph,
    PrintParagraphStyle,
    PrintQuestion,
    PrintRuledLines,
    PrintText,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
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
    make_document,
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


def _segments_paragraph(*segments: NativeSegment) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=segments)


def _free_text_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    writing_lines: int = 5,
    criteria: tuple[NativeExamCriterion, ...] = (),
) -> NativeExamItem:
    points = sum(criterion.points for criterion in criteria) if criteria else 4
    payload = make_free_text_item(sequence=sequence, item_id=item_id).model_dump()
    payload.update(
        writing_lines=writing_lines,
        points=points,
        criteria=[criterion.model_dump() for criterion in criteria],
    )
    return NativeExamItem.model_validate(payload)


def _gap_fill_item(
    body: tuple[NativeParagraph, ...],
    gaps: tuple[NativeGap, ...],
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        body=body,
        points=2,
        gaps=gaps,
        answer_key=NativeAnswerKey(origin=origin),
        review=make_review(),
    )


def _lone_gap_item(
    *, sequence: int = 1, item_id: str = "item_001", accepted: tuple[str, ...] = ("NF",)
) -> NativeExamItem:
    return _gap_fill_item(
        (_segments_paragraph(NativeGapSegment(gap_id="gap_001")),),
        (NativeGap(gap_id="gap_001", accepted_values=accepted),),
        sequence=sequence,
        item_id=item_id,
    )


def _inline_choice_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.INLINE_CHOICE,
        body=(
            _segments_paragraph(
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


def _question(document: PrintDocument, item_id: str) -> PrintQuestion:
    return next(
        entry
        for entry in document.entries
        if isinstance(entry, PrintQuestion) and entry.item_id == item_id
    )


def _all_blocks(document: PrintDocument) -> tuple[PrintBlock, ...]:
    return tuple(block for entry in document.entries for block in entry.blocks)


def _all_texts(document: PrintDocument) -> tuple[str, ...]:
    texts: list[str] = []
    for block in _all_blocks(document):
        if isinstance(block, (PrintHeading, PrintOption)):
            texts.append(block.text)
        elif isinstance(block, PrintParagraph):
            texts.extend(run.text for run in block.runs if isinstance(run, PrintText))
        elif isinstance(block, PrintGrid):
            texts.extend(block.rows)
            texts.extend(block.columns)
        elif isinstance(block, PrintAnswerKey):
            texts.extend(block.lines)
    return tuple(texts)


def _has_blank(document: PrintDocument) -> bool:
    return any(
        any(isinstance(run, PrintBlank) for run in block.runs)
        for block in _all_blocks(document)
        if isinstance(block, PrintParagraph)
    )


def _has_answer_key(document: PrintDocument) -> bool:
    return any(isinstance(block, PrintAnswerKey) for block in _all_blocks(document))


class TestHeader:
    def test_title_is_a_level_one_heading_and_details_follow(self) -> None:
        student = build_print_document(
            make_document(_free_text_item(writing_lines=5)), variant=ExamPrintVariant.STUDENT
        )

        header = student.entries[0]

        assert isinstance(header, PrintInstruction)
        assert header.blocks[0] == PrintHeading(level=1, text="Omprov: grammatik")
        assert (
            PrintParagraph(runs=(PrintText("Totalt: 4 poäng"),), style=PrintParagraphStyle.DETAIL)
            in header.blocks
        )
        assert isinstance(student.entries[1], PrintQuestion)

    def test_an_instruction_picture_becomes_an_image_run(self) -> None:
        asset = NativeExamAsset(
            asset_id=ASSET_ID, sha256="a" * 64, media_type="image/png", byte_length=10
        )
        instructions = (
            _segments_paragraph(
                NativeTextSegment(text="Läs texten ", marks=()),
                NativeAssetSegment(asset_id=ASSET_ID),
                NativeTextSegment(text=" noga.", marks=()),
            ),
        )
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Omprov: grammatik",
            instructions=instructions,
            items=(_free_text_item(),),
            assets=(asset,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        header = student.entries[0]
        assert isinstance(header, PrintInstruction)
        runs = [
            run
            for block in header.blocks
            if isinstance(block, PrintParagraph)
            for run in block.runs
        ]
        assert PrintImage(asset_id=ASSET_ID) in runs


class TestFreeText:
    def test_writing_area_follows_the_points_and_student_has_no_criteria(self) -> None:
        criterion = NativeExamCriterion(text="Kriteriet nämner renässansen", points=4)
        document = make_document(_free_text_item(writing_lines=5, criteria=(criterion,)))

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)
        question = _question(student, "item_001")

        points_index = question.blocks.index(
            PrintParagraph(runs=(PrintText("Poäng: 4 poäng"),), style=PrintParagraphStyle.POINTS)
        )
        assert question.blocks[points_index + 1] == PrintRuledLines(count=5)
        assert criterion.text not in _all_texts(student)
        assert not _has_answer_key(student)

    def test_free_text_has_no_answer_forms(self) -> None:
        student = build_print_document(
            make_document(_free_text_item(writing_lines=5)), variant=ExamPrintVariant.STUDENT
        )
        question = _question(student, "item_001")

        assert not any(isinstance(block, PrintOption) for block in question.blocks)

    def test_facit_ends_the_question_with_the_marking_guide(self) -> None:
        criterion = NativeExamCriterion(text="Kriteriet nämner renässansen", points=4)
        document = make_document(_free_text_item(writing_lines=5, criteria=(criterion,)))

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)
        question = _question(facit, "item_001")

        key = question.blocks[-1]
        assert isinstance(key, PrintAnswerKey)
        assert key.lines[0] == "Rättningsmall:"
        assert f"• {criterion.text} (4 p)" in key.lines
        assert question.blocks[-2] == PrintRuledLines(count=5)


class TestPointsFormatting:
    def test_half_points_print_with_a_comma(self) -> None:
        payload = make_single_choice_item().model_dump()
        payload.update(points=2.5)
        document = make_document(NativeExamItem.model_validate(payload))

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert (
            PrintParagraph(runs=(PrintText("Poäng: 2,5 poäng"),), style=PrintParagraphStyle.POINTS)
            in _question(student, "item_001").blocks
        )


class TestGapFill:
    def test_a_lone_gap_is_one_answer_line_with_no_blank_and_no_answer(self) -> None:
        document = make_document(_lone_gap_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)
        question = _question(student, "item_001")

        assert question.blocks[1] == PrintRuledLines(count=1)
        assert not _has_blank(student)
        assert "NF" not in _all_texts(student)

    def test_a_lone_gap_facit_lists_the_gap(self) -> None:
        document = make_document(_lone_gap_item())

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        assert _question(facit, "item_001").blocks[-1] == PrintAnswerKey(lines=("Lucka 1: NF",))

    def test_a_gap_in_a_sentence_is_a_blank_sized_for_the_longest_answer(self) -> None:
        item = _gap_fill_item(
            (
                _segments_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("ab", "fotosyntes")),),
        )

        student = build_print_document(make_document(item), variant=ExamPrintVariant.STUDENT)

        assert blank_width_mm(10) == 48.0
        assert (
            PrintParagraph(
                runs=(PrintText("Svar: "), PrintBlank(width_mm=48.0)),
                style=PrintParagraphStyle.GAP_LINE,
            )
            in _question(student, "item_001").blocks
        )
        assert "fotosyntes" not in _all_texts(student)

    def test_a_gap_in_a_sentence_facit_lists_the_accepted_values(self) -> None:
        item = _gap_fill_item(
            (
                _segments_paragraph(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
            (NativeGap(gap_id="gap_001", accepted_values=("ab", "fotosyntes")),),
        )

        facit = build_print_document(make_document(item), variant=ExamPrintVariant.FACIT)

        assert _question(facit, "item_001").blocks[-1] == PrintAnswerKey(
            lines=("Lucka 1: ab / fotosyntes",)
        )


class TestInlineChoice:
    def test_an_inline_choice_gap_prints_its_option_list_between_brackets(self) -> None:
        document = make_document(_inline_choice_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert (
            PrintParagraph(
                runs=(
                    PrintText("Vattnets formel är "),
                    PrintText("[H2O / CO2]"),
                ),
                style=PrintParagraphStyle.BODY,
            )
            in _question(student, "item_001").blocks
        )

    def test_an_inline_choice_facit_lists_the_correct_option(self) -> None:
        document = make_document(_inline_choice_item())

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        assert _question(facit, "item_001").blocks[-1] == PrintAnswerKey(lines=("Lucka 1: H2O",))


class TestChoice:
    def test_single_choice_prints_tick_options_and_the_answer_only_in_facit(self) -> None:
        document = make_document(make_single_choice_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)
        question = _question(student, "item_001")

        assert PrintOption(box=PrintBox.TICK, label="A)", text="vägen") in question.blocks
        assert PrintOption(box=PrintBox.TICK, label="B)", text="eleverna") in question.blocks
        assert not _has_answer_key(student)

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)
        assert _question(facit, "item_001").blocks[-1] == PrintAnswerKey(
            lines=("Rätt svar: eleverna",)
        )

    def test_multiple_response_prints_tick_options(self) -> None:
        payload = make_single_choice_item().model_dump()
        payload.update(kind="multiple_response")
        document = make_document(NativeExamItem.model_validate(payload))

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert (
            PrintOption(box=PrintBox.TICK, label="A)", text="vägen")
            in _question(student, "item_001").blocks
        )


class TestOrdering:
    def test_numbered_steps_print_in_the_print_order(self) -> None:
        document = make_document(make_ordering_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        options = [
            block
            for block in _question(student, "item_001").blocks
            if isinstance(block, PrintOption)
        ]
        assert options == [
            PrintOption(box=PrintBox.NUMBER, label="", text="Avslutning"),
            PrintOption(box=PrintBox.NUMBER, label="", text="Motargument"),
            PrintOption(box=PrintBox.NUMBER, label="", text="Argument"),
            PrintOption(box=PrintBox.NUMBER, label="", text="Tes"),
        ]

    def test_ordering_facit_lists_the_numbered_order(self) -> None:
        document = make_document(make_ordering_item())

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        assert _question(facit, "item_001").blocks[-1] == PrintAnswerKey(
            lines=("Rätt ordning: Avslutning 4; Motargument 3; Argument 2; Tes 1",)
        )


class TestMatching:
    def test_matching_prints_a_grid_of_the_two_lists(self) -> None:
        document = make_document(matching_item())

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert (
            PrintGrid(rows=("hund", "katt", "fågel"), columns=("däggdjur", "fåglar", "fiskar"))
            in _question(student, "item_001").blocks
        )

    def test_matching_facit_lists_the_pairs(self) -> None:
        document = make_document(matching_item())

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        assert _question(facit, "item_001").blocks[-1] == PrintAnswerKey(
            lines=(
                "Par: hund – däggdjur",
                "Par: katt – fåglar",
                "Par: fågel – fiskar",
            )
        )


class TestParents:
    def test_a_parent_instruction_prints_once_before_its_first_child(self) -> None:
        parent = NativeExamParent(
            parent_id="parent_001",
            instruction=(make_paragraph("Del 1"),),
            item_ids=("item_001", "item_002"),
        )
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Omprov: grammatik",
            items=(
                _free_text_item(sequence=1, item_id="item_001"),
                _free_text_item(sequence=2, item_id="item_002"),
            ),
            parents=(parent,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        instructions = [entry for entry in student.entries if isinstance(entry, PrintInstruction)]
        assert len(instructions) == 2  # the exam header and the one parent
        assert instructions[1].blocks == (
            PrintParagraph(runs=(PrintText("Del 1"),), style=PrintParagraphStyle.BODY),
        )
        assert isinstance(student.entries[2], PrintQuestion)
        assert student.entries[2].item_id == "item_001"
        assert isinstance(student.entries[3], PrintQuestion)
        assert student.entries[3].item_id == "item_002"
        assert len(student.entries) == 4


class TestVariants:
    def test_student_and_facit_hold_the_same_entries_apart_from_answer_keys(self) -> None:
        criterion = NativeExamCriterion(text="Kriteriet", points=4)
        document = make_document(
            _free_text_item(sequence=1, item_id="item_001", criteria=(criterion,)),
            _lone_gap_item(sequence=2, item_id="item_002"),
            make_single_choice_item(sequence=3, item_id="item_003"),
            make_ordering_item(sequence=4, item_id="item_004"),
            matching_item(sequence=5, item_id="item_005"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)
        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)

        def stripped(
            document: PrintDocument,
        ) -> tuple[tuple[str | None, tuple[PrintBlock, ...]], ...]:
            return tuple(
                (
                    entry.item_id if isinstance(entry, PrintQuestion) else None,
                    tuple(block for block in entry.blocks if not isinstance(block, PrintAnswerKey)),
                )
                for entry in document.entries
            )

        assert stripped(student) == stripped(facit)
        assert not _has_answer_key(student)
        assert _has_answer_key(facit)
        assert student.variant is ExamPrintVariant.STUDENT
        assert facit.variant is ExamPrintVariant.FACIT
        assert student.title == facit.title == "Omprov: grammatik"
