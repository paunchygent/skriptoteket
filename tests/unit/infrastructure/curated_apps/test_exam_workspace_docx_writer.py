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

from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_writer_test_support import (
    STEP_BOX,
    all_kinds_document,
    document_text,
    heading_texts,
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

        assert "Poäng: 4 poäng" in texts
        assert "Poäng: 2,5 poäng" in texts
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
