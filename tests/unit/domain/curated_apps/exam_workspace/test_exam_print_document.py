"""The format-neutral print document, student and facit (TASK-SKRIPT-40-04-07 W1-W9)."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
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
from tests.unit.domain.curated_apps.exam_workspace.exam_print_document_test_support import (
    all_texts,
    entry_blocks,
    free_text_item,
    has_answer_key,
    lone_gap_item,
    question,
    question_blocks,
    segments_paragraph,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_ordering_item,
    make_paragraph,
    make_single_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)

ASSET_ID = "asset_0123456789abcdef"


class TestHeader:
    def test_title_is_a_level_one_heading_and_details_follow(self) -> None:
        student = build_print_document(
            make_document(free_text_item(writing_lines=5)), variant=ExamPrintVariant.STUDENT
        )

        header = student.entries[0]

        assert isinstance(header, PrintInstruction)
        assert header.blocks[0] == PrintHeading(level=1, text="Omprov: grammatik")
        assert (
            PrintParagraph(
                runs=(PrintText("Totalt: 4 poäng", marks=()),),
                style=PrintParagraphStyle.DETAIL,
            )
            in header.blocks
        )
        assert isinstance(student.entries[1], PrintQuestion)

    def test_an_instruction_picture_becomes_an_image_run(self) -> None:
        asset = NativeExamAsset(
            asset_id=ASSET_ID, sha256="a" * 64, media_type="image/png", byte_length=10
        )
        instructions = (
            segments_paragraph(
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
            items=(free_text_item(),),
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
        document = make_document(free_text_item(writing_lines=5, criteria=(criterion,)))

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)
        question_entry = question(student, "item_001")

        stem_index = question_blocks(question_entry).index(
            PrintParagraph(
                runs=(
                    PrintText("Resonera om renässansen.", marks=()),
                    PrintText(" (4 p)", marks=()),
                ),
                style=PrintParagraphStyle.BODY,
            )
        )
        assert question_blocks(question_entry)[stem_index + 1] == PrintRuledLines(count=5)
        assert criterion.text not in all_texts(student)
        assert not has_answer_key(student)

    def test_free_text_has_no_answer_forms(self) -> None:
        student = build_print_document(
            make_document(free_text_item(writing_lines=5)), variant=ExamPrintVariant.STUDENT
        )
        question_entry = question(student, "item_001")

        assert not any(isinstance(block, PrintOption) for block in question_blocks(question_entry))

    def test_facit_ends_the_question_with_the_marking_guide(self) -> None:
        criterion = NativeExamCriterion(text="Kriteriet nämner renässansen", points=4)
        document = make_document(free_text_item(writing_lines=5, criteria=(criterion,)))

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)
        question_entry = question(facit, "item_001")

        key = question_blocks(question_entry)[-1]
        assert isinstance(key, PrintAnswerKey)
        assert key.lines[0] == "Rättningsmall:"
        assert f"• {criterion.text} (4 p)" in key.lines
        assert question_blocks(question_entry)[-2] == PrintRuledLines(count=5)


class TestPointsFormatting:
    def test_half_points_print_with_a_comma(self) -> None:
        payload = make_single_choice_item().model_dump()
        payload.update(points=2.5)
        document = make_document(NativeExamItem.model_validate(payload))

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert PrintParagraph(
            runs=(PrintText("Vilket är huvudordet?", marks=()), PrintText(" (2,5 p)", marks=())),
            style=PrintParagraphStyle.BODY,
        ) in question_blocks(question(student, "item_001"))


class TestParents:
    def test_a_parent_instruction_prints_once_before_its_first_child(self) -> None:
        parent = NativeExamParent(
            parent_id="parent_001",
            place=0,
            instruction=(make_paragraph("Del 1"),),
            item_ids=("item_001", "item_002"),
        )
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Omprov: grammatik",
            items=(
                free_text_item(sequence=1, item_id="item_001"),
                free_text_item(sequence=2, item_id="item_002"),
            ),
            parents=(parent,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        instructions = [entry for entry in student.entries if isinstance(entry, PrintInstruction)]
        assert len(instructions) == 2  # the exam header and the one parent
        assert instructions[1].blocks == (
            PrintParagraph(runs=(PrintText("Del 1", marks=()),), style=PrintParagraphStyle.BODY),
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
            free_text_item(sequence=1, item_id="item_001", criteria=(criterion,)),
            lone_gap_item(sequence=2, item_id="item_002"),
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
                    tuple(
                        block
                        for block in entry_blocks(entry)
                        if not isinstance(block, PrintAnswerKey)
                    ),
                )
                for entry in document.entries
            )

        assert stripped(student) == stripped(facit)
        assert not has_answer_key(student)
        assert has_answer_key(facit)
        assert student.variant is ExamPrintVariant.STUDENT
        assert facit.variant is ExamPrintVariant.FACIT
        assert student.title == facit.title == "Omprov: grammatik"


def _entry_signature(document: PrintDocument) -> tuple[tuple[str, str | None], ...]:
    """Entry types and question ids after the header, in print order."""
    return tuple(
        ("question", entry.item_id) if isinstance(entry, PrintQuestion) else ("instruction", None)
        for entry in document.entries[1:]
    )


def _part_document(
    parent: NativeExamParent,
    *items: NativeExamItem,
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=tuple(items),
        parents=(parent,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


class TestOutlineWalk:
    """The print walk reads the one outline owner, in outline order."""

    def test_part_before_standalone_prints_instruction_then_children_then_question(self) -> None:
        parent = NativeExamParent(
            parent_id="parent_001",
            place=0,
            instruction=(make_paragraph("Del 1"),),
            item_ids=("item_001", "item_002"),
        )
        document = _part_document(
            parent,
            free_text_item(sequence=1, item_id="item_001"),
            free_text_item(sequence=2, item_id="item_002"),
            free_text_item(sequence=3, item_id="item_003"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert _entry_signature(student) == (
            ("instruction", None),
            ("question", "item_001"),
            ("question", "item_002"),
            ("question", "item_003"),
        )

    def test_part_with_empty_instruction_prints_only_its_children(self) -> None:
        parent = NativeExamParent(
            parent_id="parent_001",
            place=0,
            instruction=(make_paragraph("   "),),
            item_ids=("item_001", "item_002"),
        )
        document = _part_document(
            parent,
            free_text_item(sequence=1, item_id="item_001"),
            free_text_item(sequence=2, item_id="item_002"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert _entry_signature(student) == (
            ("question", "item_001"),
            ("question", "item_002"),
        )

    def test_childless_part_with_instruction_prints_at_its_place(self) -> None:
        parent = NativeExamParent(
            parent_id="parent_001",
            place=1,
            instruction=(make_paragraph("Mellanrubrik"),),
            item_ids=(),
        )
        document = _part_document(
            parent,
            free_text_item(sequence=1, item_id="item_001"),
            free_text_item(sequence=2, item_id="item_002"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert _entry_signature(student) == (
            ("question", "item_001"),
            ("instruction", None),
            ("question", "item_002"),
        )
        instruction = student.entries[2]
        assert isinstance(instruction, PrintInstruction)
        assert instruction.blocks == (
            PrintParagraph(
                runs=(PrintText("Mellanrubrik", marks=()),),
                style=PrintParagraphStyle.BODY,
            ),
        )

    def test_childless_part_with_empty_instruction_prints_nothing(self) -> None:
        parent = NativeExamParent(
            parent_id="parent_001",
            place=1,
            instruction=(),
            item_ids=(),
        )
        document = _part_document(
            parent,
            free_text_item(sequence=1, item_id="item_001"),
            free_text_item(sequence=2, item_id="item_002"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert _entry_signature(student) == (
            ("question", "item_001"),
            ("question", "item_002"),
        )


class TestQuestionGroups:
    """PrintQuestion carries the text group and the answer-form group (K8, K13)."""

    def test_free_text_text_holds_heading_body_and_points_and_answer_holds_writing_area(
        self,
    ) -> None:
        student = build_print_document(
            make_document(free_text_item(writing_lines=5)), variant=ExamPrintVariant.STUDENT
        )
        entry = question(student, "item_001")

        assert entry.text[0] == PrintHeading(level=3, text="Fråga 1")
        assert entry.text[-1] == PrintParagraph(
            runs=(PrintText("Resonera om renässansen.", marks=()), PrintText(" (4 p)", marks=())),
            style=PrintParagraphStyle.BODY,
        )
        assert entry.answer == (PrintRuledLines(count=5),)
        assert question_blocks(entry) == entry.text + entry.answer

    def test_single_choice_text_holds_no_options_and_answer_holds_the_options(self) -> None:
        student = build_print_document(
            make_document(make_single_choice_item()), variant=ExamPrintVariant.STUDENT
        )
        entry = question(student, "item_001")

        assert entry.text[0] == PrintHeading(level=3, text="Fråga 1")
        assert entry.text[-1] == PrintParagraph(
            runs=(PrintText("Vilket är huvudordet?", marks=()), PrintText(" (1 p)", marks=())),
            style=PrintParagraphStyle.BODY,
        )
        assert not any(isinstance(block, PrintOption) for block in entry.text)
        assert entry.answer == (
            PrintOption(box=PrintBox.TICK, label="A)", runs=(PrintText("vägen", marks=()),)),
            PrintOption(box=PrintBox.TICK, label="B)", runs=(PrintText("eleverna", marks=()),)),
        )

    def test_ordering_answer_holds_the_steps_in_print_order(self) -> None:
        student = build_print_document(
            make_document(make_ordering_item()), variant=ExamPrintVariant.STUDENT
        )
        entry = question(student, "item_001")

        assert entry.text[0] == PrintHeading(level=3, text="Fråga 1")
        assert entry.text[-1] == PrintParagraph(
            runs=(
                PrintText("Sätt stegen i en argumenterande text i rätt ordning.", marks=()),
                PrintText(" (1 p)", marks=()),
            ),
            style=PrintParagraphStyle.BODY,
        )
        assert entry.answer == (
            PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Avslutning", marks=()),)),
            PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Motargument", marks=()),)),
            PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Argument", marks=()),)),
            PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Tes", marks=()),)),
        )

    def test_matching_answer_holds_the_grid(self) -> None:
        student = build_print_document(
            make_document(matching_item()), variant=ExamPrintVariant.STUDENT
        )
        entry = question(student, "item_001")

        assert entry.text[0] == PrintHeading(level=3, text="Fråga 1")
        assert entry.text[-1] == PrintParagraph(
            runs=(
                PrintText("Kategorisera orden i rätt ordklass.", marks=()),
                PrintText(" (3 p)", marks=()),
            ),
            style=PrintParagraphStyle.BODY,
        )
        assert entry.answer == (
            PrintGrid(
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
            ),
        )

    def test_facit_answer_key_is_the_last_answer_block(self) -> None:
        criterion = NativeExamCriterion(text="Kriteriet nämner renässansen", points=4)
        document = make_document(free_text_item(writing_lines=5, criteria=(criterion,)))

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)
        entry = question(facit, "item_001")

        assert entry.text[-1] == PrintParagraph(
            runs=(PrintText("Resonera om renässansen.", marks=()), PrintText(" (4 p)", marks=())),
            style=PrintParagraphStyle.BODY,
        )
        assert entry.answer[-1] == PrintAnswerKey(
            lines=("Rättningsmall:", f"• {criterion.text} (4 p)")
        )
        assert entry.answer[-2] == PrintRuledLines(count=5)
        assert not any(isinstance(block, PrintAnswerKey) for block in entry.text)
