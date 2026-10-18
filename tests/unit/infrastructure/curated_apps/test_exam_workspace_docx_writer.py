"""Round-trip and fail-closed tests for the exam workspace DOCX writer (D3)."""

import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from PIL import Image

from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body
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


_SHARED_GLOBAL_BEFORE = "Betrakta: "
_SHARED_GLOBAL_AFTER = " diagrammet."
_SHARED_PARENT_BEFORE = "Se figuren: "
_SHARED_PARENT_AFTER = " och svara."
_SHARED_MARKING_GUIDE = "Godtagbar förklaring."


@dataclass(frozen=True)
class SharedPictureDocument:
    """The accepted shared-picture document: two shared instructions and one facit item."""

    document: NativeExamDocument
    global_asset_id: str
    parent_asset_id: str
    assets_by_id: dict[str, bytes]


def _png(color: tuple[int, int, int, int], size: tuple[int, int]) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _shared_asset(payload: bytes) -> tuple[str, NativeExamAsset]:
    digest = hashlib.sha256(payload).hexdigest()
    asset_id = f"asset_{digest[:16]}"
    return asset_id, NativeExamAsset(
        asset_id=asset_id,
        media_type="image/png",
        byte_length=len(payload),
        sha256=digest,
    )


def shared_picture_document() -> SharedPictureDocument:
    """Global and parent instruction each carry a real PNG between two text runs."""
    global_payload = _png((200, 20, 20, 255), (12, 6))
    parent_payload = _png((20, 20, 200, 255), (16, 8))
    global_id, global_asset = _shared_asset(global_payload)
    parent_id, parent_asset = _shared_asset(parent_payload)
    items = (
        NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            body=(
                NativeParagraph(
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="Fråga 1.", marks=()),
                        NativeAssetSegment(asset_id=global_id),
                    ),
                ),
            ),
            points=1,
            criteria=(NativeExamCriterion(text=_SHARED_MARKING_GUIDE, points=1),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=_review_complete(),
        ),
        NativeExamItem(
            item_id="item_002",
            sequence=2,
            kind=NativeExamItemKind.FREE_TEXT,
            body=(
                NativeParagraph(
                    heading_level=None, segments=(NativeTextSegment(text="Fråga 2.", marks=()),)
                ),
            ),
            points=1,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=_review_complete(),
        ),
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Diagramprov",
        instructions=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text=_SHARED_GLOBAL_BEFORE, marks=()),
                    NativeAssetSegment(asset_id=global_id),
                    NativeTextSegment(text=_SHARED_GLOBAL_AFTER, marks=()),
                ),
            ),
        ),
        items=items,
        parents=(
            NativeExamParent(
                parent_id="parent_001",
                instruction=(
                    NativeParagraph(
                        heading_level=None,
                        segments=(
                            NativeTextSegment(text=_SHARED_PARENT_BEFORE, marks=()),
                            NativeAssetSegment(asset_id=parent_id),
                            NativeTextSegment(text=_SHARED_PARENT_AFTER, marks=()),
                        ),
                    ),
                ),
                item_ids=tuple(item.item_id for item in items),
            ),
        ),
        assets=(global_asset, parent_asset),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return SharedPictureDocument(
        document=document,
        global_asset_id=global_id,
        parent_asset_id=parent_id,
        assets_by_id={global_id: global_payload, parent_id: parent_payload},
    )


def _only_paragraph(paragraphs: list[Paragraph], text: str) -> Paragraph:
    matches = [paragraph for paragraph in paragraphs if paragraph.text == text]
    assert len(matches) == 1, f"expected one paragraph {text!r}, found {len(matches)}"
    return matches[0]


def _run_shape(paragraph: Paragraph) -> list[str]:
    shape: list[str] = []
    for run in paragraph.runs:
        if run._element.find(qn("w:drawing")) is not None:
            shape.append("image")
        elif run.text:
            shape.append(run.text)
    return shape


def _drawing_payload(parsed: DocxDocument, paragraph: Paragraph) -> bytes:
    drawing = next(
        element
        for run in paragraph.runs
        if (element := run._element.find(qn("w:drawing"))) is not None
    )
    blip = next(drawing.iter(qn("a:blip")))
    payload = parsed.part.related_parts[blip.attrib[qn("r:embed")]].blob
    assert isinstance(payload, bytes)
    return payload


def _all_kinds_document() -> NativeExamDocument:
    items = (
        NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            body=plain_body("Resonera om bisatser."),
            points=4,
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=_review_complete(),
        ),
        NativeExamItem(
            item_id="item_002",
            sequence=2,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=plain_body("Välj rätt alternativ."),
            points=1,
            choices=(
                NativeChoice(choice_id="choice_001", body=plain_body("Nominalfras")),
                NativeChoice(choice_id="choice_002", body=plain_body("Verbfras")),
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
            body=plain_body("Markera alla fraser."),
            points=2,
            choices=(
                NativeChoice(choice_id="choice_001", body=plain_body("Prepositionsfras")),
                NativeChoice(choice_id="choice_002", body=plain_body("Adjektivfras")),
                NativeChoice(choice_id="choice_003", body=plain_body("Subjunktion")),
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
                    heading_level=None,
                    segments=(
                        NativeTextSegment(text="a) Frastyp: ", marks=()),
                        NativeGapSegment(gap_id="gap_001"),
                    ),
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
        instructions=(
            NativeParagraph(
                heading_level=None, segments=(NativeTextSegment(text="Svenska 2", marks=()),)
            ),
            NativeParagraph(
                heading_level=None, segments=(NativeTextSegment(text="Total: 9,5 poäng", marks=()),)
            ),
        ),
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


class TestSharedInstructionPictures:
    def test_two_shared_instructions_round_trip_in_place_with_payloads_and_facit(self) -> None:
        fixture = shared_picture_document()
        writer = ExamWorkspaceDocxWriter()
        content = writer.build_docx_bytes(fixture.document, assets_by_id=fixture.assets_by_id)
        writer.validate_docx_bytes(content, expected_item_count=len(fixture.document.items))

        parsed = Document(io.BytesIO(content))
        paragraphs = list(parsed.paragraphs)
        texts = [paragraph.text for paragraph in paragraphs]

        global_paragraph = _only_paragraph(
            paragraphs, f"{_SHARED_GLOBAL_BEFORE}{_SHARED_GLOBAL_AFTER}"
        )
        assert _run_shape(global_paragraph) == [
            _SHARED_GLOBAL_BEFORE,
            "image",
            _SHARED_GLOBAL_AFTER,
        ]
        assert (
            _drawing_payload(parsed, global_paragraph)
            == fixture.assets_by_id[fixture.global_asset_id]
        )
        assert texts.count(global_paragraph.text) == 1

        parent_paragraph = _only_paragraph(
            paragraphs, f"{_SHARED_PARENT_BEFORE}{_SHARED_PARENT_AFTER}"
        )
        assert _run_shape(parent_paragraph) == [
            _SHARED_PARENT_BEFORE,
            "image",
            _SHARED_PARENT_AFTER,
        ]
        assert (
            _drawing_payload(parsed, parent_paragraph)
            == fixture.assets_by_id[fixture.parent_asset_id]
        )
        assert texts.count(parent_paragraph.text) == 1
        first_heading_at = next(
            index
            for index, paragraph in enumerate(paragraphs)
            if paragraph.style is not None and paragraph.style.name == "Heading 3"
        )
        assert texts.index(parent_paragraph.text) == first_heading_at - 1

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            media_payloads = [
                archive.read(name) for name in archive.namelist() if name.startswith("word/media/")
            ]
        expected_digests = sorted(
            hashlib.sha256(payload).hexdigest() for payload in fixture.assets_by_id.values()
        )
        assert sorted(hashlib.sha256(payload).hexdigest() for payload in media_payloads) == (
            expected_digests
        )

        labels = SWEDISH_EXAM_LABELS
        heading_names = [
            paragraph.text
            for paragraph in paragraphs
            if paragraph.style is not None and paragraph.style.name == "Heading 2"
        ]
        assert labels.answer_key in heading_names
        assert f"{labels.marking_guide}:" in texts
        assert f"• {_SHARED_MARKING_GUIDE} (1 p)" in texts

    def test_item_body_picture_keeps_plain_text_rendering(self) -> None:
        fixture = shared_picture_document()
        content = ExamWorkspaceDocxWriter().build_docx_bytes(
            fixture.document, assets_by_id=fixture.assets_by_id
        )

        paragraphs = list(Document(io.BytesIO(content)).paragraphs)
        body_paragraph = _only_paragraph(paragraphs, "Fråga 1.")
        assert _run_shape(body_paragraph) == ["Fråga 1."]

    def test_shared_instruction_picture_without_payload_fails_closed(self) -> None:
        fixture = shared_picture_document()
        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceDocxWriter().build_docx_bytes(fixture.document)

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details["asset_ids"] == [fixture.global_asset_id]
