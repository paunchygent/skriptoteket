"""The format-neutral print document, student and facit (TASK-SKRIPT-40-04-07 W1-W9)."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    PrintBlock,
    PrintDocument,
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
    free_text_item,
    has_answer_key,
    lone_gap_item,
    question,
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
            PrintParagraph(runs=(PrintText("Totalt: 4 poäng"),), style=PrintParagraphStyle.DETAIL)
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

        points_index = question_entry.blocks.index(
            PrintParagraph(runs=(PrintText("Poäng: 4 poäng"),), style=PrintParagraphStyle.POINTS)
        )
        assert question_entry.blocks[points_index + 1] == PrintRuledLines(count=5)
        assert criterion.text not in all_texts(student)
        assert not has_answer_key(student)

    def test_free_text_has_no_answer_forms(self) -> None:
        student = build_print_document(
            make_document(free_text_item(writing_lines=5)), variant=ExamPrintVariant.STUDENT
        )
        question_entry = question(student, "item_001")

        assert not any(isinstance(block, PrintOption) for block in question_entry.blocks)

    def test_facit_ends_the_question_with_the_marking_guide(self) -> None:
        criterion = NativeExamCriterion(text="Kriteriet nämner renässansen", points=4)
        document = make_document(free_text_item(writing_lines=5, criteria=(criterion,)))

        facit = build_print_document(document, variant=ExamPrintVariant.FACIT)
        question_entry = question(facit, "item_001")

        key = question_entry.blocks[-1]
        assert isinstance(key, PrintAnswerKey)
        assert key.lines[0] == "Rättningsmall:"
        assert f"• {criterion.text} (4 p)" in key.lines
        assert question_entry.blocks[-2] == PrintRuledLines(count=5)


class TestPointsFormatting:
    def test_half_points_print_with_a_comma(self) -> None:
        payload = make_single_choice_item().model_dump()
        payload.update(points=2.5)
        document = make_document(NativeExamItem.model_validate(payload))

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        assert (
            PrintParagraph(runs=(PrintText("Poäng: 2,5 poäng"),), style=PrintParagraphStyle.POINTS)
            in question(student, "item_001").blocks
        )


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
                    tuple(block for block in entry.blocks if not isinstance(block, PrintAnswerKey)),
                )
                for entry in document.entries
            )

        assert stripped(student) == stripped(facit)
        assert not has_answer_key(student)
        assert has_answer_key(facit)
        assert student.variant is ExamPrintVariant.STUDENT
        assert facit.variant is ExamPrintVariant.FACIT
        assert student.title == facit.title == "Omprov: grammatik"
