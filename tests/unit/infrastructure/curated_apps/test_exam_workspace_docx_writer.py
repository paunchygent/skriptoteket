"""Round-trip and fail-closed tests for the exam workspace DOCX writer (D3)."""

import io
from pathlib import Path
from uuid import uuid4

import pytest
from docx import Document

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeGap,
    NativeGapSegment,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)

ExamWorkspaceDocxWriter = exam_workspace_docx_writer.ExamWorkspaceDocxWriter

_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")


def _review_complete() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.TEACHER_CREATED,
    )


def _all_kinds_document() -> NativeExamDocument:
    items = (
        NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            body=(NativeParagraph(segments=(NativeTextSegment(text="Resonera om bisatser."),)),),
            points=4,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=_review_complete(),
        ),
        NativeExamItem(
            item_id="item_002",
            sequence=2,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=(NativeParagraph(segments=(NativeTextSegment(text="Välj rätt alternativ."),)),),
            points=1,
            choices=(
                NativeChoice(choice_id="choice_001", text="Nominalfras"),
                NativeChoice(choice_id="choice_002", text="Verbfras"),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct_choice_ids=("choice_002",),
            ),
            review=_review_complete(),
        ),
        NativeExamItem(
            item_id="item_003",
            sequence=3,
            kind=NativeExamItemKind.MULTIPLE_RESPONSE,
            body=(NativeParagraph(segments=(NativeTextSegment(text="Markera alla fraser."),)),),
            points=2,
            choices=(
                NativeChoice(choice_id="choice_001", text="Prepositionsfras"),
                NativeChoice(choice_id="choice_002", text="Adjektivfras"),
                NativeChoice(choice_id="choice_003", text="Subjunktion"),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                correct_choice_ids=("choice_001", "choice_002"),
            ),
            review=_review_complete(),
        ),
        NativeExamItem(
            item_id="item_004",
            sequence=4,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text="a) Frastyp: "),
                        NativeGapSegment(gap_id="gap_001"),
                    )
                ),
            ),
            points=2.5,
            gaps=(NativeGap(gap_id="gap_001", accepted_values=("NF", "nominalfras")),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
            review=_review_complete(),
        ),
    )
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Grammatikprov",
        instructions=("Svenska 2", "Total: 9,5 poäng"),
        items=items,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


@pytest.fixture(scope="module")
def document() -> NativeExamDocument:
    return _all_kinds_document()


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

    def test_gap_markers_points_and_choice_letters(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))
        texts = [paragraph.text for paragraph in parsed.paragraphs]

        assert "a) Frastyp: [___]" in texts
        assert "Poäng: 4 poäng" in texts
        assert "Poäng: 2,5 poäng" in texts
        assert "A) Nominalfras" in texts
        assert "B) Verbfras" in texts

    def test_facit_section_lists_keyed_answers(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))
        texts = [paragraph.text for paragraph in parsed.paragraphs]

        facit_headings = [
            paragraph.text
            for paragraph in parsed.paragraphs
            if paragraph.style is not None and paragraph.style.name == "Heading 2"
        ]
        assert "Facit" in facit_headings
        assert "Rätt svar: Verbfras" in texts
        assert "Rätt svar: Prepositionsfras; Adjektivfras" in texts
        assert "Lucka 1: NF / nominalfras" in texts

    def test_real_fixture_document_round_trips(self) -> None:
        document = NativeExamDocument.model_validate_json(_FIXTURE.read_bytes())
        content = ExamWorkspaceDocxWriter().build_docx_bytes(document)

        ExamWorkspaceDocxWriter().validate_docx_bytes(
            content, expected_item_count=len(document.items)
        )


class TestParents:
    def test_parent_instruction_is_written_once_before_its_first_child_heading(self) -> None:
        items = recorded_items()
        first, second, third = items[0], items[1], items[2]
        assert len({first.kind, second.kind, third.kind}) == 1
        parent = parent_over("parent_001", "Shared instruction for the run.", 1, 2, 3)

        content = ExamWorkspaceDocxWriter().build_docx_bytes(
            recorded_document((parent,), items=items)
        )

        parsed = Document(io.BytesIO(content))
        texts = [paragraph.text for paragraph in parsed.paragraphs]
        assert texts.count("Shared instruction for the run.") == 1
        headings = [
            p.text for p in parsed.paragraphs if p.style is not None and p.style.name == "Heading 3"
        ]
        instruction_at = texts.index("Shared instruction for the run.")
        first_heading_at = texts.index(headings[0])
        assert instruction_at == first_heading_at - 1
        assert len(headings) == len(items)

    def test_document_without_parents_writes_no_extra_paragraphs(self) -> None:
        items = recorded_items()
        plain = ExamWorkspaceDocxWriter().build_docx_bytes(recorded_document(items=items))
        parent = parent_over("parent_001", "Shared instruction for the run.", 1, 2)
        with_parent = ExamWorkspaceDocxWriter().build_docx_bytes(
            recorded_document((parent,), items=items)
        )

        plain_count = len(Document(io.BytesIO(plain)).paragraphs)
        assert len(Document(io.BytesIO(with_parent)).paragraphs) == plain_count + 1


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
