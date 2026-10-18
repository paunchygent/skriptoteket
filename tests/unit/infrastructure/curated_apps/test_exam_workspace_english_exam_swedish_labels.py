"""An exam written entirely in English still exports the Swedish added words (2026-10-18)."""

import io

from docx import Document

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_gap_fill_item,
    make_ordering_item,
    make_paragraph,
    make_single_choice_item,
)

_ENGLISH_LABELS = ("Question", "Points", "Correct order", "Correct answer", "Gap", "Image")


def _english_exam() -> NativeExamDocument:
    gap = make_gap_fill_item(sequence=1, item_id="item_001", accepted=("goes",))
    choice = make_single_choice_item(sequence=2, item_id="item_002")
    ordering = make_ordering_item(
        sequence=3, item_id="item_003", steps=("First", "Second", "Third", "Fourth")
    )
    english_gap = gap.model_copy(
        update={
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="She quickly ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                        NativeTextSegment(text=" home.", marks=()),
                    ),
                ),
            )
        }
    )
    english_choice = choice.model_copy(
        update={"body": (make_paragraph("Which word is the subject?"),)}
    )
    english_ordering = ordering.model_copy(
        update={"body": (make_paragraph("Put the sentences of the story in order."),)}
    )
    return make_document(english_gap, english_choice, english_ordering).model_copy(
        update={
            "title": "Final English test",
            "instructions": (make_paragraph("Read and answer."),),
        }
    )


def _assert_no_english_label(text: str) -> None:
    present = [label for label in _ENGLISH_LABELS if label in text]
    assert not present, present


def test_qti_titles_are_swedish_for_an_english_exam() -> None:
    items = native_exam_to_examnet_qti_items(_english_exam())
    assert [item.title for item in items] == ["Fråga 1", "Fråga 2", "Fråga 3"]
    _assert_no_english_label(
        " ".join(item.title for item in items)
        + " "
        + " ".join(gap.label for item in items for gap in item.text_entry_gaps)
    )


def test_pdf_words_are_swedish_for_an_english_exam() -> None:
    result = native_exam_to_pdf_document(_english_exam())
    assert result.status is DigiExamExamNetPdfStatus.SUCCESS, result.warnings
    assert "Fråga" in result.html
    assert "Rätt ordning" in result.html
    assert "oäng" in result.html
    _assert_no_english_label(result.html)


def test_docx_words_are_swedish_for_an_english_exam() -> None:
    content = ExamWorkspaceDocxWriter().build_docx_bytes(_english_exam())
    text = "\n".join(paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs)
    assert "Fråga 1" in text
    assert "Poäng" in text
    assert "Rätt ordning" in text
    _assert_no_english_label(text)
