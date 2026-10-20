"""Print PDF HTML in the house template, student and facit (TASK-SKRIPT-40-04-07 W1-W9)."""

import base64
import hashlib

import pytest

from skriptoteket.domain.curated_apps.exam_conversion import (
    exam_print_house_template as house_template,
)
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
    make_free_text_item,
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


def _style_text(html: str) -> str:
    """The rendered document's stylesheet text, for asserting the generated house CSS."""
    start = html.index("<style>") + len("<style>")
    return html[start : html.index("</style>")]


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

    def test_house_css_carries_the_template_page_and_body_measures(self) -> None:
        css = _style_text(_render(_document()))

        assert f"size: {house_template.PAGE_WIDTH_MM}mm {house_template.PAGE_HEIGHT_MM}mm" in css
        assert (
            f"margin: {house_template.PAGE_MARGIN_VERTICAL_MM}mm"
            f" {house_template.PAGE_MARGIN_SIDE_MM}mm" in css
        )
        assert f"font-size: {house_template.HOUSE_FONT_SIZE_PT}pt" in css
        assert "Liberation Sans" in css

    def test_house_css_carries_every_declared_heading_from_the_template(self) -> None:
        css = _style_text(_render(_document()))

        assert house_template.HEADING_GEOMETRY
        for level, geometry in house_template.HEADING_GEOMETRY.items():
            assert f"h{level} {{" in css
            assert f"font-size: {geometry.size_pt}pt" in css
            assert (
                f"margin: {geometry.spacing.space_before_mm}mm 0"
                f" {geometry.spacing.space_after_mm}mm" in css
            )

    def test_house_css_carries_the_number_box_width(self) -> None:
        css = _style_text(_render(_document()))

        assert f"width: {house_template.NUMBER_BOX_WIDTH_MM}mm" in css

    def test_a_changed_template_measure_flows_into_the_css(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(house_template, "QUESTION_SPACE_AFTER_MM", 12.5)

        css = _style_text(_render(_document()))

        assert ".print-question { margin: 0 0 12.5mm }" in css


class TestEntries:
    def test_instruction_and_question_wrappers_and_section_ids(self) -> None:
        instruction = PrintInstruction(blocks=(PrintHeading(level=1, text="Titel"),))
        question = PrintQuestion(
            item_id="item_001",
            text=(PrintHeading(level=3, text="Fråga 1"),),
            answer=(),
        )

        html = _render(_document(instruction, question))

        assert '<div class="print-instruction">' in html
        assert '<section class="print-question" id="exam-item-item_001">' in html
        assert "<h1>Titel</h1>" in html
        assert "<h3>Fråga 1</h3>" in html

    def test_the_section_id_is_escaped(self) -> None:
        question = PrintQuestion(
            item_id='item_001"><script>',
            text=(PrintHeading(level=3, text="Fråga"),),
            answer=(),
        )

        html = _render(_document(question))

        assert 'id="exam-item-item_001&quot;&gt;&lt;script&gt;"' in html
        assert "<script>" not in html


class TestBlocks:
    def test_five_ruled_lines_render_five_writing_lines(self) -> None:
        question = PrintQuestion(item_id="item_001", text=(), answer=(PrintRuledLines(count=5),))

        html = _render(_document(question))

        assert html.count('class="writing-line"') == 5
        assert '<div class="writing-area"><div class="writing-line"></div>' in html

    def test_a_gap_line_paragraph_keeps_its_style_and_blank_width(self) -> None:
        width = blank_width_mm(9)
        question = PrintQuestion(
            item_id="item_001",
            text=(
                PrintParagraph(
                    runs=(PrintText("Svar: ", ()), PrintBlank(width_mm=width)),
                    style=PrintParagraphStyle.GAP_LINE,
                ),
            ),
            answer=(),
        )

        html = _render(_document(question))

        assert width == 44.0
        assert 'class="print-gap_line"' in html
        assert f'<span class="gap-blank" style="width:{width:.1f}mm"></span>' in html

    def test_text_runs_are_escaped(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            text=(
                PrintParagraph(
                    runs=(PrintText('<b>& "x"', ()),),
                    style=PrintParagraphStyle.BODY,
                ),
            ),
            answer=(),
        )

        html = _render(_document(question))

        assert "&lt;b&gt;&amp; &quot;x&quot;" in html
        assert "<b>&" not in html

    def test_tick_options_render_the_glyph_and_number_options_render_the_box(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            text=(),
            answer=(
                PrintOption(box=PrintBox.TICK, label="A)", runs=(PrintText("vägen", ()),)),
                PrintOption(box=PrintBox.NUMBER, label="", runs=(PrintText("Tes", ()),)),
            ),
        )

        html = _render(_document(question))

        assert f'<p class="print-option">{house_template.TICK_BOX_GLYPH} A) vägen</p>' in html
        assert '<p class="print-option"><span class="number-box"></span> Tes</p>' in html
        assert html.count(house_template.TICK_BOX_GLYPH) == 1

    def test_a_grid_renders_a_header_and_one_glyph_cell_per_row_and_column(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            text=(),
            answer=(
                PrintGrid(
                    rows=((PrintText("hund", ()),), (PrintText("katt", ()),)),
                    columns=(
                        (PrintText("däggdjur", ()),),
                        (PrintText("fåglar", ()),),
                        (PrintText("fiskar", ()),),
                    ),
                ),
            ),
        )

        html = _render(_document(question))

        assert '<th scope="col">däggdjur</th>' in html
        assert '<th scope="row">hund</th>' in html
        cell = f"<td>{house_template.TICK_BOX_GLYPH}</td>"
        assert cell in html
        assert html.count(cell) == 6

    def test_an_answer_key_renders_one_paragraph_per_line(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            text=(),
            answer=(PrintAnswerKey(lines=("Rätt svar: eleverna", "Poäng: 1")),),
        )

        html = _render(_document(question, variant=ExamPrintVariant.FACIT))

        assert (
            '<div class="print-answer-key"><p>Rätt svar: eleverna</p><p>Poäng: 1</p></div>' in html
        )


class TestMarkedRuns:
    def _body_question(self, *runs: PrintText) -> PrintQuestion:
        return PrintQuestion(
            item_id="item_001",
            text=(PrintParagraph(runs=tuple(runs), style=PrintParagraphStyle.BODY),),
            answer=(),
        )

    def test_body_paragraph_renders_bold_and_combined_marks(self) -> None:
        question = self._body_question(
            PrintText("Diskutera", ("bold",)),
            PrintText(" hur ", ()),
            PrintText("x", ("bold", "italic", "underline")),
        )

        html = _render(_document(question))

        assert (
            '<p class="print-body"><strong>Diskutera</strong>'
            " hur <strong><em><u>x</u></em></strong></p>" in html
        )

    def test_superscript_and_subscript_runs_render(self) -> None:
        question = self._body_question(
            PrintText("x", ("superscript",)),
            PrintText("y", ("subscript",)),
        )

        html = _render(_document(question))

        assert "<sup>x</sup><sub>y</sub>" in html

    def test_hard_break_renders_br_and_stays_inside_marks(self) -> None:
        plain = _render(_document(self._body_question(PrintText("rad ett\nrad två", ()))))

        assert "rad ett<br>rad två" in plain

        marked = _render(_document(self._body_question(PrintText("rad ett\nrad två", ("bold",)))))

        assert "<strong>rad ett<br>rad två</strong>" in marked

    def test_escaping_holds_inside_marks(self) -> None:
        question = self._body_question(PrintText('<b>& "x"', ("bold",)))

        html = _render(_document(question))

        assert "<strong>&lt;b&gt;&amp; &quot;x&quot;</strong>" in html

    def test_option_runs_print_their_marks(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            text=(),
            answer=(
                PrintOption(
                    box=PrintBox.TICK,
                    label="A)",
                    runs=(PrintText("vägen", ("bold",)),),
                ),
            ),
        )

        html = _render(_document(question))

        assert f"{house_template.TICK_BOX_GLYPH} A) <strong>vägen</strong>" in html

    def test_grid_cell_runs_print_their_marks(self) -> None:
        question = PrintQuestion(
            item_id="item_001",
            text=(),
            answer=(
                PrintGrid(
                    rows=((PrintText("hund", ("italic",)),),),
                    columns=((PrintText("däggdjur", ("bold",)),),),
                ),
            ),
        )

        html = _render(_document(question))

        assert '<th scope="col"><strong>däggdjur</strong></th>' in html
        assert '<th scope="row"><em>hund</em></th>' in html

    def test_body_and_gap_line_paragraphs_use_body_spacing(self) -> None:
        css = _style_text(_render(_document()))

        assert "p.print-body, p.print-gap_line { margin: 0mm 0 4mm }" in css
        assert (
            f"p {{ margin: {house_template.PARAGRAPH_SPACING.space_before_mm}mm 0 "
            f"{house_template.PARAGRAPH_SPACING.space_after_mm}mm;"
            " break-inside: avoid }" in css
        )

    def test_end_to_end_bold_word_and_two_paragraphs(self) -> None:
        from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
            NativeParagraph,
            NativeTextSegment,
        )

        item = make_single_choice_item()
        first = NativeParagraph(
            heading_level=None,
            segments=(
                NativeTextSegment(text="Läs ", marks=()),
                NativeTextSegment(text="noga", marks=("bold",)),
            ),
        )
        second = NativeParagraph(
            heading_level=None,
            segments=(NativeTextSegment(text="Andra stycket.", marks=()),),
        )
        bold_item = make_free_text_item().model_copy(update={"body": (first, second)})
        document = make_document(bold_item)

        html = _render(
            build_print_document(document, variant=ExamPrintVariant.STUDENT),
            assets=(),
            assets_by_id={},
        )

        assert "<strong>noga</strong>" in html
        assert html.count('<p class="print-body">') == 2
        assert item.item_id  # the choice builder still shapes options elsewhere


class TestKeepTogetherGroups:
    def _question(self) -> PrintQuestion:
        return PrintQuestion(
            item_id="item_001",
            text=(
                PrintHeading(level=3, text="Fråga 1"),
                PrintParagraph(
                    runs=(PrintText("Brödtext.", ()), PrintText(" (2 p)", ())),
                    style=PrintParagraphStyle.BODY,
                ),
            ),
            answer=(
                PrintRuledLines(count=2),
                PrintOption(box=PrintBox.TICK, label="A)", runs=(PrintText("vägen", ()),)),
                PrintOption(box=PrintBox.TICK, label="B)", runs=(PrintText("skolan", ()),)),
            ),
        )

    def test_text_group_contains_heading_body_and_points(self) -> None:
        html = _render(_document(self._question()))
        text_start = html.index('<div class="print-question-text">')
        options_start = html.index('<div class="print-options">')
        text_slice = html[text_start:options_start]

        assert "<h3>Fråga 1</h3>" in text_slice
        assert "Brödtext. (2 p)" in text_slice

    def test_consecutive_options_share_one_wrapper(self) -> None:
        html = _render(_document(self._question()))

        assert html.count('<div class="print-options">') == 1
        options_start = html.index('<div class="print-options">')
        options_slice = html[options_start : html.index("</section>")]
        assert "A) vägen" in options_slice
        assert "B) skolan" in options_slice

    def test_writing_area_renders_outside_the_text_group(self) -> None:
        html = _render(_document(self._question()))
        text_start = html.index('<div class="print-question-text">')
        text_end = html.index("</div>", text_start)

        assert "writing-area" not in html[text_start:text_end]
        assert html.count('class="writing-line"') == 2

    def test_house_css_keeps_groups_together_and_instruction_with_question(self) -> None:
        css = _style_text(_render(_document(self._question())))

        assert ".print-question-text { break-inside: avoid }" in css
        assert ".print-options { break-inside: avoid }" in css
        assert "p.print-body, p.print-option" not in css
        assert (
            f"p {{ margin: {house_template.PARAGRAPH_SPACING.space_before_mm}mm 0 "
            f"{house_template.PARAGRAPH_SPACING.space_after_mm}mm;"
            " break-inside: avoid }" in css
        )
        assert ".print-grid tr { break-inside: avoid }" in css
        assert ".print-instruction {" in css
        assert "break-after: avoid;" in css

    def test_writing_area_may_split_while_single_lines_do_not(self) -> None:
        css = _style_text(_render(_document(self._question())))

        assert ".writing-area { break-inside" not in css
        assert ".writing-line {" in css


class TestPictures:
    def _image_question(self) -> PrintQuestion:
        return PrintQuestion(
            item_id="item_001",
            text=(
                PrintParagraph(
                    runs=(PrintText("Se ", ()), PrintImage(asset_id=ASSET_ID)),
                    style=PrintParagraphStyle.BODY,
                ),
            ),
            answer=(),
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
        assert f"{house_template.TICK_BOX_GLYPH} A) vägen" in student_html

        assert "<title>Omprov: grammatik – Facit</title>" in facit_html
        assert '<div class="print-answer-key">' in facit_html
        assert "<p>Rätt svar: eleverna</p>" in facit_html

    def test_a_sized_blank_prints_its_computed_width(self) -> None:
        item = make_gap_fill_item(accepted=("ABCDEFGHI",))
        expected_width = blank_width_mm(9)

        html = _render(build_print_document(make_document(item), variant=ExamPrintVariant.STUDENT))

        assert 'class="print-gap_line"' in html
        assert f'style="width:{expected_width:.1f}mm"' in html


class TestRenderedPage:
    def test_a_full_student_document_renders_one_a4_page(self) -> None:
        from weasyprint import HTML

        document = build_print_document(
            make_document(make_single_choice_item()), variant=ExamPrintVariant.STUDENT
        )
        rendered = HTML(string=_render(document)).render()

        assert rendered.write_pdf().startswith(b"%PDF")
        page = rendered.pages[0]
        assert page.width * 72 / 96 == pytest.approx(595.28, abs=0.5)
        assert page.height * 72 / 96 == pytest.approx(841.89, abs=0.5)
