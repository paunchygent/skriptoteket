"""Kept-answer links print as plain words and never as gaps (TASK-SKRIPT-40-04-13 H1)."""

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    PrintParagraph,
    PrintText,
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.exam_print_document_test_support import (
    all_texts,
    has_answer_key,
    has_blank,
    question,
    question_blocks,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_review,
)


def kept_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Ange frastyp: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text=" Ordet ", marks=()),
                    NativeTextSegment(text="nominalfras", marks=("bold",), kept_gap_id="gap_002"),
                    NativeTextSegment(text=" kvar.", marks=()),
                ),
            ),
        ),
        points=2,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=("VF",)),),
        kept_gaps=(NativeGap(gap_id="gap_002", accepted_values=("KEPTSECRET",)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=make_review(),
    )


class TestPrintDocumentKeptGaps:
    def test_student_print_shows_the_kept_word_as_plain_text(self) -> None:
        student = build_print_document(make_document(kept_item()), variant=ExamPrintVariant.STUDENT)
        texts = all_texts(student)
        runs = [
            run
            for block in question_blocks(question(student, "item_001"))
            if isinstance(block, PrintParagraph)
            for run in block.runs
            if isinstance(run, PrintText)
        ]

        assert "nominalfras" in "".join(texts)
        assert "KEPTSECRET" not in "".join(texts)
        assert has_blank(student)
        assert not has_answer_key(student)
        assert any(run.text == "nominalfras" for run in runs)

    def test_facit_key_lists_live_gaps_only(self) -> None:
        facit = build_print_document(make_document(kept_item()), variant=ExamPrintVariant.FACIT)
        keys = [
            block
            for block in question_blocks(question(facit, "item_001"))
            if isinstance(block, PrintAnswerKey)
        ]
        lines = [line for block in keys for line in block.lines]

        assert has_answer_key(facit)
        assert any("VF" in line for line in lines)
        assert all("KEPTSECRET" not in line for line in lines)
