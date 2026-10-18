"""Print PDF HTML in the house template, student and facit (TASK-SKRIPT-40-04-07 W1-W9)."""

import base64
import hashlib

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
    blank_width_mm,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintAnswerKey,
    PrintBlank,
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
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_html import (
    render_print_html,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_gap_fill_item,
    make_single_choice_item,
)

ASSET_ID = "asset_0123456789abcdef"
PNG_PAYLOAD = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def _asset(
    payload: bytes,
    *,
    media_type: str = "image/png",
    sha256: str | None = None,
    byte_length: int | None = None,
) -> NativeExamAsset:
    return NativeExamAsset(
        asset_id=ASSET_ID,
        sha256=sha256 if sha256 is not None else hashlib.sha256(payload).hexdigest(),
        media_type=media_type,
        byte_length=byte_length if byte_length is not None else len(payload),
    )


def _document(
    *entries: PrintInstruction | PrintQuestion,
    variant: ExamPrintVariant = ExamPrintVariant.STUDENT,
    title: str = "Omprov: grammatik",
) -> PrintDocument:
    return PrintDocument(variant=variant, title=title, entries=tuple(entries))


def _render(
    document: PrintDocument,
    *,
    assets: tuple[NativeExamAsset, ...] = (),
    assets_by_id: dict[str, bytes] | None = None,
) -> str:
    return render_print_html(document, assets=assets, assets_by_id=assets_by_id or {})


class TestDocumentShell:
    def test_student_title_carries_the_variant_suffix(self) -> None:
        html = _render(_document())

        assert "<title>Omprov: grammatik – Elevexemplar</title>" in html
        assert '<html lang="sv">' in html
        assert '<meta charset="utf-8">' in html

    def test_facit_title_carries_its_variant_suffix(self) -> None:
        html = _render(_document(variant=ExamPrintVariant.FACIT))

        assert "<title>Omprov: grammatik – Facit</title>" in html

    def test_the_title_is_escaped(self) -> None:
        html = _render(_document(title='A <B> & "C"'))

        assert "<title>A &lt;B&gt; &amp;" in html

    def test_house_css_uses_the_template_measures(self) -> None:
        html = _render(_document())

        assert "10.0mm" in html
        assert "Liberation Sans" in html
        assert "@page { size: A4; margin: 18.0mm 18.0mm; }" in html
        assert "font-size: 12pt" in html


class TestEntries:
    def test_instruction_and_question_wrappers_and_section_ids(self) -> None:
        instruction = PrintInstruction(blocks=(PrintHeading(level=1, text="Titel"),))
        question = PrintQuestion(
            item_id="item_001",
            blocks=(PrintHeading(level=3, text="Fråga 1"),),
        )

        html = _render(_document(instruction, question))

        assert '<div class="print-instruction">' in html
        assert '<section class="print-question" id="exam-item-item_001">' in html
        assert "<h1>Titel</h1>" in html
        assert "<h3>Fråga 1</h3>" in html

    def test_the_section_id_is_escaped(self) -> None:
        question = PrintQuestion(
            item_id='item_001"><script>',
            blocks=(PrintHeading(level=3, text="Fråga"),),
        )

        html = _render(_document(question))

        assert 'id="exam-item-item_001&quot;&gt;&lt;script&gt;"' in html
        assert "<script>" not in html


class TestBlocks:
    def test_five_ruled_lines_render_five_writing_lines(self) -> None:
        question = PrintQuestion(item_id="item_001", blocks=(PrintRuledLines(count=5),))

        html = _render(_document(question))

        assert html.count('class="writing-line"') == 5
        assert '<div class="writing-area"><div class="writing-line"></div>' in html

    def test_a_gap_line_paragraph_keeps_its_style_and_blank_width(self) -> None:
        width = blank_width_mm(9)
        question = PrintQuestion(
            item_id="item_001",
            blocks=(
                PrintParagraph(
                    runs=(PrintText("Svar: "), PrintBlank(width_mm=width)),
                    style=PrintParagraphStyle.GAP_LINE,
                ),
            ),
        )

        html = _render(_document(question))

        assert width == 44.0
        assert 'class="print-gap_line"' in html
        assert f'<span class="gap-blank" style="width:{width:.1f}mm"></span>' in html

    def test_text_runs_are_escaped(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            blocks=(
                PrintParagraph(
                    runs=(PrintText('<b>& "x"'),),
                    style=PrintParagraphStyle.BODY,
                ),
            ),
        )

        html = _render(_document(question))

        assert "&lt;b&gt;&amp; &quot;x&quot;" in html
        assert "<b>&" not in html

    def test_tick_and_number_options_render_their_boxes(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            blocks=(
                PrintOption(box=PrintBox.TICK, label="A)", text="vägen"),
                PrintOption(box=PrintBox.NUMBER, label="", text="Tes"),
            ),
        )

        html = _render(_document(question))

        assert '<p class="print-option"><span class="tick-box"></span> A) vägen</p>' in html
        assert '<p class="print-option"><span class="number-box"></span> Tes</p>' in html

    def test_a_grid_renders_a_header_and_one_tick_cell_per_row_and_column(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            blocks=(PrintGrid(rows=("hund", "katt"), columns=("däggdjur", "fåglar", "fiskar")),),
        )

        html = _render(_document(question))

        assert '<th scope="col">däggdjur</th>' in html
        assert '<th scope="row">hund</th>' in html
        assert '<td><span class="tick-box"></span></td>' in html
        assert html.count('<td><span class="tick-box"></span></td>') == 6

    def test_an_answer_key_renders_one_paragraph_per_line(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            blocks=(PrintAnswerKey(lines=("Rätt svar: eleverna", "Poäng: 1")),),
        )

        html = _render(_document(question, variant=ExamPrintVariant.FACIT))

        assert (
            '<div class="print-answer-key"><p>Rätt svar: eleverna</p><p>Poäng: 1</p></div>' in html
        )


class TestPictures:
    def _image_question(self) -> PrintQuestion:
        return PrintQuestion(
            item_id="item_001",
            blocks=(
                PrintParagraph(
                    runs=(PrintText("Se "), PrintImage(asset_id=ASSET_ID)),
                    style=PrintParagraphStyle.BODY,
                ),
            ),
        )

    def test_a_valid_payload_is_inlined_as_a_data_uri(self) -> None:
        asset = _asset(PNG_PAYLOAD)
        html = _render(
            _document(self._image_question()),
            assets=(asset,),
            assets_by_id={ASSET_ID: PNG_PAYLOAD},
        )

        expected = "data:image/png;base64," + base64.b64encode(PNG_PAYLOAD).decode("ascii")
        assert f'<img class="print-image" src="{expected}" alt="Bild">' in html

    def test_a_missing_payload_raises(self) -> None:
        asset = _asset(PNG_PAYLOAD)

        with pytest.raises(DomainError) as exc_info:
            _render(_document(self._image_question()), assets=(asset,), assets_by_id={})

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details == {"asset_ids": [ASSET_ID]}

    def test_a_sha256_mismatch_raises(self) -> None:
        other = bytes(byte ^ 0xFF for byte in PNG_PAYLOAD)
        asset = _asset(PNG_PAYLOAD)

        with pytest.raises(DomainError) as exc_info:
            _render(
                _document(self._image_question()),
                assets=(asset,),
                assets_by_id={ASSET_ID: other},
            )

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert exc_info.value.details == {"asset_ids": [ASSET_ID]}

    def test_a_byte_length_mismatch_raises(self) -> None:
        asset = _asset(PNG_PAYLOAD, byte_length=len(PNG_PAYLOAD) + 1)

        with pytest.raises(DomainError) as exc_info:
            _render(
                _document(self._image_question()),
                assets=(asset,),
                assets_by_id={ASSET_ID: PNG_PAYLOAD},
            )

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


class TestBuiltDocuments:
    def test_student_and_facit_variants_of_one_choice_document(self) -> None:
        document = make_document(make_single_choice_item())

        student_html = _render(build_print_document(document, variant=ExamPrintVariant.STUDENT))
        facit_html = _render(build_print_document(document, variant=ExamPrintVariant.FACIT))

        assert "<title>Omprov: grammatik – Elevexemplar</title>" in student_html
        assert '<div class="print-answer-key">' not in student_html
        assert 'id="exam-item-item_001"' in student_html
        assert '<span class="tick-box"></span> A) vägen' in student_html

        assert "<title>Omprov: grammatik – Facit</title>" in facit_html
        assert '<div class="print-answer-key">' in facit_html
        assert "<p>Rätt svar: eleverna</p>" in facit_html

    def test_a_sized_blank_prints_its_computed_width(self) -> None:
        item = make_gap_fill_item(accepted=("ABCDEFGHI",))
        expected_width = blank_width_mm(9)

        html = _render(build_print_document(make_document(item), variant=ExamPrintVariant.STUDENT))

        assert 'class="print-gap_line"' in html
        assert f'style="width:{expected_width:.1f}mm"' in html
