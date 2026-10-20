"""Content, house-template and fail-closed tests for the exam workspace DOCX writer (D3).

The Word export is the student copy (W2) rendered from the print document; these tests read
the produced bytes back with python-docx and inspect the paragraph XML. The printed
answer-form geometry lives in the answer-forms suite and the shared-picture round trips in
the pictures suite.
"""

import io
from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    BODY_PARAGRAPH_SPACING,
    PARAGRAPH_SPACING,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_writer_test_support import (
    STEP_BOX,
    all_kinds_document,
    document_text,
    heading_texts,
    only_paragraph,
)

ExamWorkspaceDocxWriter = exam_workspace_docx_writer.ExamWorkspaceDocxWriter

_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")


@pytest.fixture(scope="module")
def document() -> NativeExamDocument:
    return all_kinds_document()


@pytest.fixture(scope="module")
def docx_bytes(document: NativeExamDocument) -> bytes:
    return ExamWorkspaceDocxWriter().build_docx_bytes(document)


class TestDocxContent:
    def test_round_trip_validation_passes(
        self, docx_bytes: bytes, document: NativeExamDocument
    ) -> None:
        ExamWorkspaceDocxWriter().validate_docx_bytes(
            docx_bytes, expected_item_count=len(document.items)
        )

    def test_title_instructions_and_item_headings(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))
        texts = [paragraph.text for paragraph in parsed.paragraphs]

        assert "Grammatikprov" in texts
        assert "Svenska 2" in texts
        # Items carry no title (39-05-08); headings are the question labels.
        assert "Fråga 1" in texts
        assert "Fråga 2" in texts

    def test_points_and_tick_options_without_gap_markers(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))
        texts = [paragraph.text for paragraph in parsed.paragraphs]

        assert "Resonera om bisatser. (4 p)" in texts
        assert "Välj rätt alternativ. (1 p)" in texts
        assert "Markera alla fraser. (2 p)" in texts
        assert any(text.startswith("a) Frastyp: ") and text.endswith(" (2,5 p)") for text in texts)
        assert f"{STEP_BOX} A) Nominalfras" in texts
        assert f"{STEP_BOX} B) Verbfras" in texts
        assert "[___]" not in document_text(parsed)

    def test_student_copy_carries_no_answer_key_or_criterion(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))
        text = document_text(parsed)

        assert SWEDISH_EXAM_LABELS.answer_key not in heading_texts(parsed, "Heading 2")
        assert "Facit" not in text
        assert "Kriteriet nämner bisatser" not in text
        assert "nominalfras" not in text
        # The correct choice is still a printed option, so the student sees the wording.
        assert f"{STEP_BOX} B) Verbfras" in text

    def test_real_fixture_document_round_trips(self) -> None:
        document = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes())
        content = ExamWorkspaceDocxWriter().build_docx_bytes(document)

        ExamWorkspaceDocxWriter().validate_docx_bytes(
            content, expected_item_count=len(document.items)
        )


class TestHouseTemplate:
    def test_normal_style_is_the_house_font_and_margins(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))

        normal = parsed.styles["Normal"]
        assert normal.font.name == "Liberation Sans"
        assert normal.font.size.pt == 12
        assert normal.paragraph_format.line_spacing == 1.5

        section = parsed.sections[0]
        for margin in (
            section.left_margin,
            section.right_margin,
            section.top_margin,
            section.bottom_margin,
        ):
            assert margin is not None
            assert margin.mm == pytest.approx(18, abs=0.05)


class TestValidationFailsClosed:
    def test_corrupt_bytes_rejected(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceDocxWriter().validate_docx_bytes(b"not a docx", expected_item_count=1)

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_wrong_item_heading_count_rejected(self, docx_bytes: bytes) -> None:
        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceDocxWriter().validate_docx_bytes(docx_bytes, expected_item_count=5)

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details["found_item_headings"] == 4


def _marked_body_item() -> NativeExamItem:
    body = (
        NativeParagraph(
            heading_level=None,
            segments=(
                NativeTextSegment(text="Diskutera", marks=("bold",)),
                NativeTextSegment(text=" hur ", marks=()),
            ),
        ),
        NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Andra stycket.", marks=()),),
        ),
    )
    return make_free_text_item().model_copy(update={"body": body})


class TestPrintedMarksAndBodySpacing:
    def test_bold_run_keeps_bold_and_plain_run_keeps_none(self) -> None:
        document = make_document(_marked_body_item())
        parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))
        paragraph = only_paragraph(list(parsed.paragraphs), "Diskutera hur ")
        by_text = {run.text: run for run in paragraph.runs}

        assert by_text["Diskutera"].bold is True
        assert by_text[" hur "].bold is None

    def test_two_body_paragraphs_carry_the_body_spacing(self) -> None:
        document = make_document(_marked_body_item())
        parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))

        for text in ("Diskutera hur ", "Andra stycket. (4 p)"):
            paragraph = only_paragraph(list(parsed.paragraphs), text)
            assert paragraph.paragraph_format.space_after is not None
            assert paragraph.paragraph_format.space_after.mm == pytest.approx(
                BODY_PARAGRAPH_SPACING.space_after_mm, abs=0.02
            )

    def test_each_mark_sets_only_its_word_property(self) -> None:
        body = (
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="kursiv", marks=("italic",)),
                    NativeTextSegment(text="under", marks=("underline",)),
                    NativeTextSegment(text="upp", marks=("superscript",)),
                    NativeTextSegment(text="ner", marks=("subscript",)),
                    NativeTextSegment(text="vanlig", marks=()),
                ),
            ),
        )
        item = make_free_text_item().model_copy(update={"body": body, "points": None})
        parsed = Document(
            io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(make_document(item)))
        )
        paragraph = only_paragraph(list(parsed.paragraphs), "kursivunderuppnervanlig")
        by_text = {run.text: run for run in paragraph.runs}

        assert by_text["kursiv"].italic is True
        assert by_text["kursiv"].bold is None
        assert by_text["under"].underline is True
        assert by_text["under"].bold is None
        assert by_text["upp"].font.superscript is True
        assert by_text["upp"].font.subscript is False
        assert by_text["ner"].font.subscript is True
        assert by_text["ner"].font.superscript is False
        plain = by_text["vanlig"]
        assert plain.bold is None
        assert plain.italic is None
        assert plain.underline is None
        assert plain.font.superscript is None
        assert plain.font.subscript is None

    def test_hard_break_inside_a_run_writes_a_word_line_break(self) -> None:
        body = (
            NativeParagraph(
                heading_level=None,
                segments=(NativeTextSegment(text="a\nb", marks=()),),
            ),
        )
        item = make_free_text_item().model_copy(update={"body": body, "points": None})
        parsed = Document(
            io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(make_document(item)))
        )
        paragraph = only_paragraph(list(parsed.paragraphs), "a\nb")

        breaks = [element for run in paragraph.runs for element in run._element.iter(qn("w:br"))]
        assert len(breaks) == 1

    def test_header_detail_line_keeps_the_plain_paragraph_spacing(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))
        detail = only_paragraph(list(parsed.paragraphs), "Totalt: 9,5 poäng")

        assert detail.paragraph_format.space_after is not None
        assert detail.paragraph_format.space_after.mm == pytest.approx(
            PARAGRAPH_SPACING.space_after_mm, abs=0.02
        )
