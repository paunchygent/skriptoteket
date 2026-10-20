"""The print document's stored text marks (TASK-SKRIPT-40-04-20 D1, D6, D7)."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintBox,
    PrintGrid,
    PrintInstruction,
    PrintOption,
    PrintParagraph,
    PrintParagraphStyle,
    PrintText,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeChoice,
)
from tests.unit.domain.curated_apps.exam_workspace.exam_print_document_test_support import (
    free_text_item,
    inline_choice_item,
    question,
    segments_paragraph,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_paragraph,
    make_single_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)


class TestTextMarks:
    """Printed runs keep the native body's stored marks (TASK-SKRIPT-40-04-20 D1, D6, D7)."""

    def test_shared_instruction_keeps_bold_words_in_both_paragraphs(self) -> None:
        instructions = (
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Diskutera", marks=("bold",)),
                    NativeTextSegment(text=" hur Kims ", marks=()),
                    NativeTextSegment(text="beteende och rädsla", marks=("bold",)),
                ),
            ),
            segments_paragraph(NativeTextSegment(text="Andra stycket.", marks=())),
        )
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Omprov: grammatik",
            instructions=instructions,
            items=(free_text_item(),),
            origin=NativeExamDocumentOrigin(kind="created"),
        )

        student = build_print_document(document, variant=ExamPrintVariant.STUDENT)

        header = student.entries[0]
        assert isinstance(header, PrintInstruction)
        bodies = [
            block
            for block in header.blocks
            if isinstance(block, PrintParagraph) and block.style is PrintParagraphStyle.BODY
        ]
        assert bodies == [
            PrintParagraph(
                runs=(
                    PrintText("Diskutera", marks=("bold",)),
                    PrintText(" hur Kims ", marks=()),
                    PrintText("beteende och rädsla", marks=("bold",)),
                ),
                style=PrintParagraphStyle.BODY,
            ),
            PrintParagraph(
                runs=(PrintText("Andra stycket.", marks=()),),
                style=PrintParagraphStyle.BODY,
            ),
        ]

    def test_question_body_keeps_mark_order_and_points_run_has_no_marks(self) -> None:
        item = free_text_item().model_copy(
            update={
                "body": (
                    NativeParagraph(
                        heading_level=None,
                        segments=(
                            NativeTextSegment(
                                text="Förklara ",
                                marks=("bold", "italic", "underline"),
                            ),
                            NativeTextSegment(text="x", marks=("superscript",)),
                        ),
                    ),
                )
            }
        )

        student = build_print_document(make_document(item), variant=ExamPrintVariant.STUDENT)

        assert question(student, "item_001").text[-1] == PrintParagraph(
            runs=(
                PrintText("Förklara ", marks=("bold", "italic", "underline")),
                PrintText("x", marks=("superscript",)),
                PrintText(" (4 p)", marks=()),
            ),
            style=PrintParagraphStyle.BODY,
        )

    def test_body_heading_paragraph_prints_its_runs_bold_without_duplicates(self) -> None:
        item = free_text_item().model_copy(
            update={
                "body": (
                    NativeParagraph(
                        heading_level=2,
                        segments=(NativeTextSegment(text="Bakgrund", marks=("italic",)),),
                    ),
                    NativeParagraph(
                        heading_level=2,
                        segments=(NativeTextSegment(text="Syfte", marks=("bold",)),),
                    ),
                )
            }
        )

        student = build_print_document(make_document(item), variant=ExamPrintVariant.STUDENT)

        bodies = [
            block
            for block in question(student, "item_001").text
            if isinstance(block, PrintParagraph)
        ]
        assert bodies[0] == PrintParagraph(
            runs=(PrintText("Bakgrund", marks=("bold", "italic")),),
            style=PrintParagraphStyle.BODY,
        )
        assert bodies[1] == PrintParagraph(
            runs=(
                PrintText("Syfte", marks=("bold",)),
                PrintText(" (4 p)", marks=()),
            ),
            style=PrintParagraphStyle.BODY,
        )

    def test_single_choice_option_runs_keep_marks_and_join_paragraphs_with_a_break(
        self,
    ) -> None:
        item = make_single_choice_item().model_copy(
            update={
                "choices": (
                    NativeChoice(
                        choice_id="choice_001",
                        body=(
                            NativeParagraph(
                                heading_level=None,
                                segments=(
                                    NativeTextSegment(text="vä", marks=()),
                                    NativeTextSegment(text="gen", marks=("bold",)),
                                ),
                            ),
                            segments_paragraph(NativeTextSegment(text="fortsättning", marks=())),
                        ),
                    ),
                    NativeChoice(choice_id="choice_002", body=(make_paragraph("eleverna"),)),
                )
            }
        )

        student = build_print_document(make_document(item), variant=ExamPrintVariant.STUDENT)

        options = [
            block
            for block in question(student, "item_001").answer
            if isinstance(block, PrintOption)
        ]
        assert options[0] == PrintOption(
            box=PrintBox.TICK,
            label="A)",
            runs=(
                PrintText("vä", marks=()),
                PrintText("gen", marks=("bold",)),
                PrintText("\n", marks=()),
                PrintText("fortsättning", marks=()),
            ),
        )

    def test_matching_grid_cell_keeps_its_marks(self) -> None:
        item = matching_item()
        underlined = NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="hund", marks=("underline",)),),
        )
        item = item.model_copy(
            update={
                "match_left": (
                    NativeMatchLeft(left_id=item.match_left[0].left_id, body=(underlined,)),
                    *item.match_left[1:],
                )
            }
        )

        student = build_print_document(make_document(item), variant=ExamPrintVariant.STUDENT)

        grid = question(student, "item_001").answer[0]
        assert isinstance(grid, PrintGrid)
        assert grid.rows[0] == (PrintText("hund", marks=("underline",)),)

    def test_inline_choice_bracket_run_carries_no_marks(self) -> None:
        student = build_print_document(
            make_document(inline_choice_item()), variant=ExamPrintVariant.STUDENT
        )

        runs = [
            run
            for block in question(student, "item_001").text
            if isinstance(block, PrintParagraph)
            for run in block.runs
            if isinstance(run, PrintText)
        ]

        assert runs[0] == PrintText("Vattnets formel är ", marks=())
        assert next(run for run in runs if run.text.startswith("[")) == PrintText(
            "[H2O / CO2]", marks=()
        )
