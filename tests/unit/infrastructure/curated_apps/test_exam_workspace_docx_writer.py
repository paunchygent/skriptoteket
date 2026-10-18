"""Round-trip, house-template and fail-closed tests for the exam workspace DOCX writer (D3).

The Word export is the student copy (W2) rendered from the print document; these tests read
the produced bytes back with python-docx and inspect the paragraph XML, so they cover the
ruled writing lines (W4, W9), the gap rules (W6, W7), the tick forms (W8) and the absence of
every answer.
"""

import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Mm
from docx.text.paragraph import Paragraph
from PIL import Image

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    TEXT_WIDTH_MM,
)
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
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_ordering_item,
    make_single_choice_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)

ExamWorkspaceDocxWriter = exam_workspace_docx_writer.ExamWorkspaceDocxWriter

_FIXTURE = Path("tests/fixtures/exam_conversion/native_workspace_grammatik.json")
_STEP_BOX = "☐"
_NBSP = "\u00a0"


def _review_complete() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.TEACHER_CREATED,
    )


_SHARED_GLOBAL_BEFORE = "Betrakta: "
_SHARED_GLOBAL_AFTER = " diagrammet."
_SHARED_PARENT_BEFORE = "Se figuren: "
_SHARED_PARENT_AFTER = " och svara."


@dataclass(frozen=True)
class SharedPictureDocument:
    """The accepted shared-picture document: two shared instructions and two free-text items."""

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
            writing_lines=8,
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
            criteria=(NativeExamCriterion(text="Godtagbar förklaring.", points=1),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
            review=_review_complete(),
        ),
        NativeExamItem(
            item_id="item_002",
            sequence=2,
            kind=NativeExamItemKind.FREE_TEXT,
            writing_lines=8,
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


def _document_text(parsed: DocxDocument) -> str:
    parts = [paragraph.text for paragraph in parsed.paragraphs]
    for table in parsed.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def _heading_texts(parsed: DocxDocument, heading: str) -> list[str]:
    return [
        paragraph.text
        for paragraph in parsed.paragraphs
        if paragraph.style is not None and paragraph.style.name == heading
    ]


def _border_edges(paragraph: Paragraph) -> tuple[str, ...] | None:
    pPr = paragraph._p.find(qn("w:pPr"))
    if pPr is None:
        return None
    borders = pPr.find(qn("w:pBdr"))
    if borders is None:
        return None
    return tuple(child.tag.split("}")[1] for child in borders)


def _border_attributes(paragraph: Paragraph, edge: str) -> dict[str, str | None]:
    pPr = paragraph._p.find(qn("w:pPr"))
    assert pPr is not None
    borders = pPr.find(qn("w:pBdr"))
    assert borders is not None
    element = borders.find(qn(f"w:{edge}"))
    assert element is not None
    return {name: element.get(qn(f"w:{name}")) for name in ("val", "sz", "space", "color")}


def _ruled_paragraphs(paragraphs: list[Paragraph]) -> list[Paragraph]:
    return [paragraph for paragraph in paragraphs if _border_edges(paragraph) is not None]


def _blank_run_count(paragraph: Paragraph) -> int:
    blanks = [
        run
        for run in paragraph.runs
        if run.font.underline and run.text and set(run.text) == {_NBSP}
    ]
    assert len(blanks) == 1, f"expected one underlined blank run, found {len(blanks)}"
    return len(blanks[0].text)


def _free_text_item(*, writing_lines: int, item_id: str = "item_001") -> NativeExamItem:
    payload = make_free_text_item(item_id=item_id).model_dump()
    payload.update(writing_lines=writing_lines)
    return NativeExamItem.model_validate(payload)


def _gap_fill_item(
    body: tuple[NativeParagraph, ...],
    gaps: tuple[NativeGap, ...],
    *,
    item_id: str = "item_001",
    sequence: int = 1,
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
        review=_review_complete(),
    )


def _lone_gap_item() -> NativeExamItem:
    return _gap_fill_item(
        (NativeParagraph(heading_level=None, segments=(NativeGapSegment(gap_id="gap_001"),)),),
        (NativeGap(gap_id="gap_001", accepted_values=("NF",)),),
    )


def _sentence_gap_item(
    accepted: tuple[str, ...],
    *,
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
) -> NativeExamItem:
    return _gap_fill_item(
        (
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Svar: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
        ),
        (NativeGap(gap_id="gap_001", accepted_values=accepted),),
        origin=origin,
    )


def _all_kinds_document() -> NativeExamDocument:
    items = (
        NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.FREE_TEXT,
            writing_lines=8,
            body=plain_body("Resonera om bisatser."),
            points=4,
            criteria=(NativeExamCriterion(text="Kriteriet nämner bisatser", points=4),),
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

    def test_points_and_tick_options_without_gap_markers(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))
        texts = [paragraph.text for paragraph in parsed.paragraphs]

        assert "Poäng: 4 poäng" in texts
        assert "Poäng: 2,5 poäng" in texts
        assert f"{_STEP_BOX} A) Nominalfras" in texts
        assert f"{_STEP_BOX} B) Verbfras" in texts
        assert "[___]" not in _document_text(parsed)

    def test_student_copy_carries_no_answer_key_or_criterion(self, docx_bytes: bytes) -> None:
        parsed = Document(io.BytesIO(docx_bytes))
        text = _document_text(parsed)

        assert SWEDISH_EXAM_LABELS.answer_key not in _heading_texts(parsed, "Heading 2")
        assert "Facit" not in text
        assert "Kriteriet nämner bisatser" not in text
        assert "nominalfras" not in text
        # The correct choice is still a printed option, so the student sees the wording.
        assert f"{_STEP_BOX} B) Verbfras" in text

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


class TestWritingArea:
    @pytest.mark.parametrize("count", [5, 1])
    def test_free_text_prints_exactly_its_writing_lines(self, count: int) -> None:
        document = make_document(_free_text_item(writing_lines=count))
        parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))
        paragraphs = list(parsed.paragraphs)

        points_at = next(
            index
            for index, paragraph in enumerate(paragraphs)
            if paragraph.text == "Poäng: 4 poäng"
        )
        # A free-text question ends with its writing area, so the points line's tail is it.
        ruled = paragraphs[points_at + 1 :]
        assert len(ruled) == count
        for paragraph in ruled:
            assert paragraph.text == ""
            assert _border_edges(paragraph) == ("bottom", "between")
            expected = {"val": "single", "sz": "4", "space": "0", "color": "555555"}
            assert _border_attributes(paragraph, "bottom") == expected
            assert _border_attributes(paragraph, "between") == expected
            spacing = paragraph.paragraph_format
            assert spacing.line_spacing.mm == pytest.approx(10, abs=0.01)
            assert spacing.line_spacing_rule is WD_LINE_SPACING.EXACTLY


class TestGapRules:
    def test_a_lone_gap_is_one_ruled_line_and_no_gap_marker(self) -> None:
        parsed = Document(
            io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(make_document(_lone_gap_item())))
        )

        assert len(_ruled_paragraphs(list(parsed.paragraphs))) == 1
        assert "[___]" not in _document_text(parsed)

    @pytest.mark.parametrize(
        ("accepted", "origin", "expected_count"),
        [
            (("ab", "fotosyntes"), NativeAnswerKeyOrigin.SOURCE_PROVIDED, 41),
            (("nominalfras",), NativeAnswerKeyOrigin.SOURCE_PROVIDED, 45),
            ((), NativeAnswerKeyOrigin.ABSENT, 26),
        ],
    )
    def test_a_sentence_gap_is_an_underlined_blank_sized_for_its_answer(
        self,
        accepted: tuple[str, ...],
        origin: NativeAnswerKeyOrigin,
        expected_count: int,
    ) -> None:
        document = make_document(_sentence_gap_item(accepted, origin=origin))
        parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))

        paragraph = _only_paragraph(list(parsed.paragraphs), "Svar: " + _NBSP * expected_count)
        assert paragraph.runs[0].text == "Svar: "
        assert _blank_run_count(paragraph) == expected_count
        assert paragraph.paragraph_format.line_spacing.mm == pytest.approx(10, abs=0.01)
        assert paragraph.paragraph_format.line_spacing_rule is WD_LINE_SPACING.EXACTLY
        for value in accepted:
            assert value not in _document_text(parsed)


class TestForms:
    def test_single_choice_prints_tick_options(self) -> None:
        document = make_document(make_single_choice_item())
        parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))
        texts = [paragraph.text for paragraph in parsed.paragraphs]

        assert f"{_STEP_BOX} A) vägen" in texts
        assert f"{_STEP_BOX} B) eleverna" in texts
        assert "Facit" not in _document_text(parsed)

    def test_ordering_prints_tick_options_in_print_order(self) -> None:
        document = make_document(make_ordering_item())
        parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))

        options = [
            paragraph.text
            for paragraph in parsed.paragraphs
            if paragraph.text.startswith(_STEP_BOX)
        ]
        assert options == [
            f"{_STEP_BOX} Avslutning",
            f"{_STEP_BOX} Motargument",
            f"{_STEP_BOX} Argument",
            f"{_STEP_BOX} Tes",
        ]

    def test_matching_prints_a_grid_with_tick_cells(self) -> None:
        document = make_document(matching_item())
        parsed = Document(io.BytesIO(ExamWorkspaceDocxWriter().build_docx_bytes(document)))

        assert len(parsed.tables) == 1
        table = parsed.tables[0]
        assert len(table.rows) == 4
        assert len(table.columns) == 4
        assert [cell.text for cell in table.rows[0].cells] == ["", "däggdjur", "fåglar", "fiskar"]
        assert [cell.text for cell in table.rows[1].cells] == [
            "hund",
            _STEP_BOX,
            _STEP_BOX,
            _STEP_BOX,
        ]


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
        headings = _heading_texts(parsed, "Heading 3")
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


class TestPictures:
    def test_two_shared_instructions_round_trip_in_place_with_payloads(self) -> None:
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
        first_heading_at = texts.index(_heading_texts(parsed, "Heading 3")[0])
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

        assert SWEDISH_EXAM_LABELS.answer_key not in _heading_texts(parsed, "Heading 2")
        assert "Godtagbar förklaring." not in _document_text(parsed)

    def test_item_body_picture_is_embedded(self) -> None:
        fixture = shared_picture_document()
        content = ExamWorkspaceDocxWriter().build_docx_bytes(
            fixture.document, assets_by_id=fixture.assets_by_id
        )

        parsed = Document(io.BytesIO(content))
        # The global instruction, item_001's body and the parent instruction each embed one.
        assert len(parsed.inline_shapes) == 3
        body_paragraph = _only_paragraph(list(parsed.paragraphs), "Fråga 1.")
        assert _run_shape(body_paragraph) == ["Fråga 1.", "image"]
        assert (
            _drawing_payload(parsed, body_paragraph)
            == fixture.assets_by_id[fixture.global_asset_id]
        )

    def test_picture_wider_than_the_text_column_is_clamped(self) -> None:
        payload = _png((10, 90, 10, 255), (4000, 40))
        asset_id, asset = _shared_asset(payload)
        item = make_free_text_item()
        item = NativeExamItem.model_validate(
            {
                **item.model_dump(),
                "body": [
                    {
                        "heading_level": None,
                        "segments": [
                            {"kind": "text", "text": "Se bilden", "marks": []},
                            {"kind": "asset", "asset_id": asset_id},
                        ],
                    }
                ],
            }
        )
        document = NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Bildprov",
            items=(item,),
            assets=(asset,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )

        content = ExamWorkspaceDocxWriter().build_docx_bytes(
            document, assets_by_id={asset_id: payload}
        )
        parsed = Document(io.BytesIO(content))
        assert len(parsed.inline_shapes) == 1
        assert parsed.inline_shapes[0].width == Mm(TEXT_WIDTH_MM)

    def test_picture_without_payload_fails_closed(self) -> None:
        fixture = shared_picture_document()
        with pytest.raises(DomainError) as exc_info:
            ExamWorkspaceDocxWriter().build_docx_bytes(fixture.document)

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details["asset_ids"] == [fixture.global_asset_id]
