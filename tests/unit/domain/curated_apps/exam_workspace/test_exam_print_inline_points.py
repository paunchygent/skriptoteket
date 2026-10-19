"""Fail-first tests for inline "(N p)" points in the printed exam (TASK-SKRIPT-40-04-15 U1).

Each question's points print as "(N p)" at the end of its last question-text paragraph,
and no separate "Poäng:" line prints. These tests pin that behaviour against the rendered
print HTML for the STUDENT and FACIT variants; they fail on the current code, which still
renders the "Poäng: N poäng" paragraph. The Exam.net export keeps its import-oriented
points line, so its case passes now and must keep passing.
"""

from html.parser import HTMLParser

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_html import (
    render_print_html,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.exam_print_document_test_support import (
    segments_paragraph,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_paragraph,
    make_review,
    plain_body,
)

_VARIANTS = (ExamPrintVariant.STUDENT, ExamPrintVariant.FACIT)


def _choice_item(
    *,
    item_id: str,
    sequence: int,
    body: tuple[NativeParagraph, ...],
    points: int | float | None,
    alternatives: tuple[str, ...],
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=body,
        points=points,
        choices=tuple(
            NativeChoice(choice_id=f"choice_{index:03d}", body=plain_body(text))
            for index, text in enumerate(alternatives, start=1)
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            correct_choice_ids=("choice_001",),
        ),
        review=make_review(),
    )


def _free_text_item(
    *,
    item_id: str,
    sequence: int,
    body: tuple[NativeParagraph, ...],
    points: int | float | None,
    writing_lines: int = 3,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=body,
        points=points,
        writing_lines=writing_lines,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=make_review(),
    )


def _gap_fill_item(
    *,
    item_id: str,
    sequence: int,
    points: int | float | None,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            make_paragraph("Fyll i luckan."),
            segments_paragraph(
                NativeTextSegment(text="Ange frastyp: ", marks=()),
                NativeGapSegment(gap_id="gap_001"),
            ),
        ),
        points=points,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=("NF",)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=make_review(),
    )


def _inline_points_document() -> NativeExamDocument:
    return make_document(
        _choice_item(
            item_id="item_001",
            sequence=1,
            body=(make_paragraph("Vilket problem prövas?"),),
            points=1,
            alternatives=("vägen", "eleverna"),
        ),
        _choice_item(
            item_id="item_002",
            sequence=2,
            body=(
                make_paragraph("Första meningen."),
                make_paragraph("Andra meningen."),
                make_paragraph("Tredje meningen."),
            ),
            points=2,
            alternatives=("vägen", "eleverna"),
        ),
        _choice_item(
            item_id="item_003",
            sequence=3,
            body=(make_paragraph("Vilket ord är verb?"),),
            points=1,
            alternatives=("hus", "springer", "och", "blå"),
        ),
        _free_text_item(
            item_id="item_004",
            sequence=4,
            body=(make_paragraph("Resonera om renässansen."),),
            points=4,
            writing_lines=5,
        ),
        _gap_fill_item(item_id="item_005", sequence=5, points=2),
        _free_text_item(item_id="item_006", sequence=6, body=(), points=2),
        _free_text_item(
            item_id="item_007",
            sequence=7,
            body=(make_paragraph("Nollpoängsfrågan."),),
            points=0,
        ),
        _free_text_item(
            item_id="item_008",
            sequence=8,
            body=(make_paragraph("Halvpoängsfrågan."),),
            points=1.5,
        ),
        _free_text_item(
            item_id="item_009",
            sequence=9,
            body=(make_paragraph("Frågan saknar poängvärde."),),
            points=None,
        ),
    )


class _SectionBlocks:
    """One print-question section's blocks in render order, parsed without regex."""

    def __init__(self) -> None:
        class _Parser(HTMLParser):
            def __init__(self, outer: "_SectionBlocks") -> None:
                super().__init__(convert_charrefs=True)
                self.outer = outer

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                self.outer._start(tag, dict(attrs))

            def handle_data(self, data: str) -> None:
                self.outer._data(data)

            def handle_endtag(self, tag: str) -> None:
                self.outer._end(tag)

        self._parser = _Parser(self)
        self.sections: dict[str, list[tuple[str, str, str, str]]] = {}
        self._section: str | None = None
        self._div_stack: list[str] = []
        self._capture: list[str] | None = None
        self._capture_tag = ""
        self._capture_class = ""

    def feed(self, html: str) -> "_SectionBlocks":
        self._parser.feed(html)
        return self

    def _start(self, tag: str, attrs: dict[str, str | None]) -> None:
        if tag == "section" and "print-question" in (attrs.get("class") or ""):
            self._section = (attrs.get("id") or "").removeprefix("exam-item-")
            self.sections[self._section] = []
        elif self._section is not None and tag == "div":
            classes = attrs.get("class") or ""
            self._div_stack.append(classes)
            if "writing-area" in classes:
                self.sections[self._section].append(("div", classes, "", ""))
        elif self._section is not None and tag in ("p", "h3"):
            self._capture = []
            self._capture_tag = tag
            self._capture_class = attrs.get("class") or ""

    def _data(self, data: str) -> None:
        if self._capture is not None:
            self._capture.append(data)

    def _end(self, tag: str) -> None:
        if tag == "section":
            self._section = None
        elif tag == "div" and self._section is not None and self._div_stack:
            self._div_stack.pop()
        elif tag in ("p", "h3") and self._capture is not None and self._section is not None:
            container = self._div_stack[-1] if self._div_stack else ""
            self.sections[self._section].append(
                (self._capture_tag, container, self._capture_class, "".join(self._capture))
            )
            self._capture = None


def _rendered(variant: ExamPrintVariant) -> tuple[str, _SectionBlocks]:
    html = render_print_html(
        build_print_document(_inline_points_document(), variant=variant),
        assets=(),
        assets_by_id={},
    )
    return html, _SectionBlocks().feed(html)


def _texts(
    sections: _SectionBlocks,
    item_id: str,
    *,
    tag: str = "p",
    container: str = "print-question-text",
    css_class: str,
) -> list[str]:
    return [
        text
        for block_tag, block_container, block_class, text in sections.sections[item_id]
        if block_tag == tag and block_container == container and block_class == css_class
    ]


def _heading(sections: _SectionBlocks, item_id: str) -> str:
    headings = [
        text
        for block_tag, _container, _class, text in sections.sections[item_id]
        if block_tag == "h3"
    ]
    assert len(headings) == 1
    return headings[0]


@pytest.mark.parametrize("variant", _VARIANTS)
def test_single_paragraph_stem_ends_with_inline_points(variant: ExamPrintVariant) -> None:
    _html, sections = _rendered(variant)

    bodies = _texts(sections, "item_001", css_class="print-body")

    assert bodies == ["Vilket problem prövas? (1 p)"]


@pytest.mark.parametrize("variant", _VARIANTS)
def test_only_the_last_of_three_stem_paragraphs_carries_points(
    variant: ExamPrintVariant,
) -> None:
    _html, sections = _rendered(variant)

    bodies = _texts(sections, "item_002", css_class="print-body")

    assert len(bodies) == 3
    assert "p)" not in bodies[0]
    assert "p)" not in bodies[1]
    assert bodies[2].endswith(" (2 p)")


@pytest.mark.parametrize("variant", _VARIANTS)
def test_choice_stem_carries_points_but_options_do_not(variant: ExamPrintVariant) -> None:
    _html, sections = _rendered(variant)

    stems = _texts(sections, "item_003", css_class="print-body")
    options = _texts(sections, "item_003", container="print-options", css_class="print-option")

    assert len(stems) == 1
    assert stems[0].endswith(" (1 p)")
    assert len(options) == 4
    assert all("(1 p)" not in option for option in options)


@pytest.mark.parametrize("variant", _VARIANTS)
def test_free_text_stem_carries_points_before_the_writing_area(
    variant: ExamPrintVariant,
) -> None:
    _html, sections = _rendered(variant)
    blocks = sections.sections["item_004"]

    stems = _texts(sections, "item_004", css_class="print-body")
    writing_areas = [
        index
        for index, (tag, container, _css_class, _text) in enumerate(blocks)
        if tag == "div" and "writing-area" in container
    ]
    assert writing_areas, "writing area is missing"
    writing_area = writing_areas[0]
    last_stem = max(
        index
        for index, (tag, container, css_class, _text) in enumerate(blocks)
        if tag == "p" and container == "print-question-text" and css_class == "print-body"
    )

    assert stems == ["Resonera om renässansen. (4 p)"]
    assert last_stem < writing_area


@pytest.mark.parametrize("variant", _VARIANTS)
def test_gap_line_last_paragraph_carries_points_after_the_blank(
    variant: ExamPrintVariant,
) -> None:
    _html, sections = _rendered(variant)

    gap_lines = _texts(sections, "item_005", css_class="print-gap_line")

    assert gap_lines
    assert gap_lines[-1].endswith(" (2 p)")


@pytest.mark.parametrize("variant", _VARIANTS)
def test_question_without_a_text_paragraph_carries_points_in_the_heading(
    variant: ExamPrintVariant,
) -> None:
    _html, sections = _rendered(variant)

    assert _heading(sections, "item_006") == "Fråga 6 (2 p)"
    assert _texts(sections, "item_006", css_class="print-body") == []
    assert _texts(sections, "item_006", css_class="print-gap_line") == []


@pytest.mark.parametrize("variant", _VARIANTS)
def test_zero_and_fractional_points_use_a_decimal_comma(variant: ExamPrintVariant) -> None:
    _html, sections = _rendered(variant)

    assert _texts(sections, "item_007", css_class="print-body") == ["Nollpoängsfrågan. (0 p)"]
    assert _texts(sections, "item_008", css_class="print-body") == ["Halvpoängsfrågan. (1,5 p)"]


@pytest.mark.parametrize("variant", _VARIANTS)
def test_missing_points_prints_no_points_text_and_keeps_the_heading(
    variant: ExamPrintVariant,
) -> None:
    _html, sections = _rendered(variant)

    assert _heading(sections, "item_009") == "Fråga 9"
    combined = "".join(text for _tag, _container, _class, text in sections.sections["item_009"])

    assert "p)" not in combined
    assert "Poäng" not in combined


@pytest.mark.parametrize("variant", _VARIANTS)
def test_no_separate_points_line_anywhere(variant: ExamPrintVariant) -> None:
    html, _sections = _rendered(variant)

    assert "Poäng:" not in html
    assert "print-points" not in html


def test_examnet_pdf_keeps_its_current_points_lines() -> None:
    document = _inline_points_document()
    pointed = tuple(item for item in document.items if item.points is not None)
    renderable = tuple(item for item in pointed if item.body)
    resequenced = tuple(
        NativeExamItem.model_validate({**item.model_dump(), "sequence": index})
        for index, item in enumerate(renderable, start=1)
    )
    examnet_document = make_document(*resequenced)

    rendered = native_exam_to_pdf_document(examnet_document)

    assert rendered.status is DigiExamExamNetPdfStatus.SUCCESS
    assert rendered.html.count('class="points"') == len(renderable)
    for item in renderable:
        assert f"Poängvärde: {item.points}" in rendered.html
