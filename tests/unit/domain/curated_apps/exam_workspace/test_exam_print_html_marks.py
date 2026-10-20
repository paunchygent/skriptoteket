"""Marked text runs in the print PDF HTML (TASK-SKRIPT-40-04-20, review F1/F3)."""

from collections.abc import Iterator

from weasyprint import HTML
from weasyprint.document import Page
from weasyprint.formatting_structure.boxes import Box, TextBox

from skriptoteket.domain.curated_apps.exam_conversion import (
    exam_print_house_template as house_template,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    PrintBox,
    PrintGrid,
    PrintOption,
    PrintParagraph,
    PrintParagraphStyle,
    PrintQuestion,
    PrintText,
    build_print_document,
)
from tests.unit.domain.curated_apps.exam_workspace.exam_print_html_test_support import (
    document,
    render,
    style_text,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_single_choice_item,
)


def _walk(box: Box) -> Iterator[Box]:
    yield box
    for child in box.children:
        yield from _walk(child)


def _grid_text_weights(page: Page) -> dict[str, list[int]]:
    """Computed font weights per grid-label text box on one laid-out page."""
    weights: dict[str, list[int]] = {}
    for box in _walk(page._page_box):
        if isinstance(box, TextBox) and box.text in ("Plain ", "Bold"):
            weight = box.style["font_weight"]
            assert isinstance(weight, int)
            weights.setdefault(box.text, []).append(weight)
    return weights


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

        html = render(document(question))

        assert (
            '<p class="print-body"><strong>Diskutera</strong>'
            " hur <strong><em><u>x</u></em></strong></p>" in html
        )

    def test_superscript_and_subscript_runs_render(self) -> None:
        question = self._body_question(
            PrintText("x", ("superscript",)),
            PrintText("y", ("subscript",)),
        )

        html = render(document(question))

        assert "<sup>x</sup><sub>y</sub>" in html

    def test_hard_break_renders_br_and_stays_inside_marks(self) -> None:
        plain = render(document(self._body_question(PrintText("rad ett\nrad två", ()))))

        assert "rad ett<br>rad två" in plain

        marked = render(document(self._body_question(PrintText("rad ett\nrad två", ("bold",)))))

        assert "<strong>rad ett<br>rad två</strong>" in marked

    def test_escaping_holds_inside_marks(self) -> None:
        question = self._body_question(PrintText('<b>& "x"', ("bold",)))

        html = render(document(question))

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

        html = render(document(question))

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

        html = render(document(question))

        assert '<th scope="col"><strong>däggdjur</strong></th>' in html
        assert '<th scope="row"><em>hund</em></th>' in html

    def test_grid_labels_keep_plain_text_plain_in_the_rendered_page(self) -> None:
        cell = (PrintText("Plain ", ()), PrintText("Bold", ("bold",)))
        question = PrintQuestion(
            item_id="item_001",
            text=(),
            answer=(PrintGrid(rows=(cell,), columns=(cell,)),),
        )

        rendered = HTML(string=render(document(question))).render()
        weights = _grid_text_weights(rendered.pages[0])

        assert weights["Plain "] == [400, 400]
        assert weights["Bold"] == [700, 700]

    def test_body_and_gap_line_paragraphs_use_body_spacing(self) -> None:
        css = style_text(render(document()))

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
        native_document = make_document(bold_item)

        html = render(
            build_print_document(native_document, variant=ExamPrintVariant.STUDENT),
            assets=(),
            assets_by_id={},
        )

        assert "<strong>noga</strong>" in html
        assert html.count('<p class="print-body">') == 2
        assert item.item_id  # the choice builder still shapes options elsewhere
