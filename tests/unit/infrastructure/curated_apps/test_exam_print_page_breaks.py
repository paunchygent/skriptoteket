"""Fail-first page-break tests for printed PDF exams (TASK-SKRIPT-40-04-12, unit 1).

Each case lays out the production print HTML with WeasyPrint
(``build_print_document`` -> ``render_print_html`` -> ``HTML(string=...).render()``)
for STUDENT and FACIT over a sweep of preceding heights, and asserts on which
page each marked text lands. The K1, K3/K4, K5/K14, K12 and K15 cases FAIL on the
current code, which prints a question as flat sibling blocks with no
keep-together groups; the K2 case passes. Unit 3 (HTML and CSS groups) makes
this file pass; nothing is marked xfail.
"""

from collections.abc import Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from weasyprint import HTML
from weasyprint.document import Document, Page
from weasyprint.formatting_structure.boxes import Box, TextBox

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_html import (
    render_print_html,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
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
    gap_fill_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_ordering_item,
    make_paragraph,
    make_review,
    make_single_choice_item,
    plain_body,
)

VARIANTS = (ExamPrintVariant.STUDENT, ExamPrintVariant.FACIT)
HEIGHTS = tuple(range(0, 40, 2))


def _walk(box: Box) -> Iterator[Box]:
    yield box
    for child in box.children:
        yield from _walk(child)


def _class_list(box: Box) -> list[str]:
    element = box.element
    if element is None:
        return []
    classes = element.get("class")
    if classes is None:
        return []
    return classes.split()


def _walk_outside_answer_key(box: Box) -> Iterator[Box]:
    """Every box except the facit answer key's, whose lines repeat steps and rows."""
    if "print-answer-key" in _class_list(box):
        return
    yield box
    for child in box.children:
        yield from _walk_outside_answer_key(child)


def _page_texts(page: Page) -> str:
    return "".join(
        box.text for box in _walk_outside_answer_key(page._page_box) if isinstance(box, TextBox)
    )


def _render(document: NativeExamDocument, variant: ExamPrintVariant) -> Document:
    html = render_print_html(
        build_print_document(document, variant=variant),
        assets=document.assets,
        assets_by_id={},
    )
    return HTML(string=html).render()


def _pages_with(rendered: Document, marker: str) -> set[int]:
    return {
        number for number, page in enumerate(rendered.pages, start=1) if marker in _page_texts(page)
    }


def _line_pages(rendered: Document) -> set[int]:
    """Pages holding at least one ruled writing line."""
    found: set[int] = set()
    for number, page in enumerate(rendered.pages, start=1):
        for box in _walk(page._page_box):
            if box.element_tag == "div" and "writing-line" in _class_list(box):
                found.add(number)
                break
    return found


def _filler(lines: int) -> NativeExamItem:
    """Preceding content of a sweep height: a free-text question with N writing lines."""
    base = make_free_text_item(sequence=1, item_id="item_001")
    return base.model_copy(
        update={
            "points": 1,
            "writing_lines": max(lines, 1),
            "body": (make_paragraph("Fylltext FYLL."),),
        }
    )


def _k1_item() -> NativeExamItem:
    """Omprov Fråga 3: instruction paragraphs plus numbered items in the body."""
    base = make_free_text_item(sequence=2, item_id="item_002")
    return base.model_copy(
        update={
            "points": 4,
            "writing_lines": 2,
            "body": (
                make_paragraph("Identifiera huvudord K1INSTR."),
                make_paragraph("Stryk under huvudordet i varje nominalfras."),
                make_paragraph("1. de tre nya eleverna från Göteborg"),
                make_paragraph("2. min äldre systers trasiga mobiltelefon på köksbordet"),
                make_paragraph("3. alla böckerna i den nedersta hyllan"),
                make_paragraph("4. den lilla vägen genom skogen K1SISTA"),
            ),
        }
    )


def _choice_item() -> NativeExamItem:
    base = make_single_choice_item(sequence=2, item_id="item_002")
    choices = tuple(
        NativeChoice(choice_id=f"choice_{index:03d}", body=plain_body(f"Alternativ VAL{index}"))
        for index in range(1, 7)
    )
    return base.model_copy(
        update={
            "points": 2,
            "body": (make_paragraph("Vilket är huvudordet VALTEXT?"),),
            "choices": choices,
            "answer_key": NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct_choice_ids=("choice_002",),
            ),
        }
    )


def _matching_item() -> NativeExamItem:
    return NativeExamItem(
        item_id="item_002",
        sequence=2,
        kind=NativeExamItemKind.MATCHING,
        body=(make_paragraph("Matcha orden MATCHTEXT."),),
        points=4,
        tick_points=Decimal("1"),
        match_left=tuple(
            NativeMatchLeft(left_id=f"left_{index:03d}", body=plain_body(f"Ord MATCHL{index}"))
            for index in range(1, 5)
        ),
        match_right=tuple(
            NativeMatchRight(
                right_id=f"right_{index:03d}",
                body=plain_body(f"Betydelse MATCHR{index}"),
            )
            for index in range(1, 5)
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            match_pairs=tuple(
                NativeMatchPair(left_id=f"left_{index:03d}", right_id=f"right_{index:03d}")
                for index in range(1, 5)
            ),
        ),
        review=make_review(),
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("filler_lines", HEIGHTS)
def test_k1_question_text_stays_on_one_page(variant: ExamPrintVariant, filler_lines: int) -> None:
    """K1: heading, instruction, items and points move to the next page together."""
    rendered = _render(make_document(_filler(filler_lines), _k1_item()), variant)
    heading = _pages_with(rendered, "Fråga 2")
    instruction = _pages_with(rendered, "K1INSTR")
    last_item = _pages_with(rendered, "K1SISTA")
    points = _pages_with(rendered, "Poäng: 4 poäng")
    assert heading == instruction == last_item == points and len(heading) == 1, (
        f"N={filler_lines} {variant.value}: {len(rendered.pages)} pages, "
        f"heading={sorted(heading)} instruction={sorted(instruction)} "
        f"item4={sorted(last_item)} points={sorted(points)}"
    )


def test_k1_sweep_reaches_a_page_end() -> None:
    """The K1 sweep proves something: some height pushes the question onto page 2+."""
    starts = [
        min(_pages_with(_render(make_document(_filler(n), _k1_item()), variant), "Fråga 2"))
        for variant in VARIANTS
        for n in HEIGHTS
    ]
    assert any(page >= 2 for page in starts), f"no height reached page 2: {starts}"


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("filler_lines", HEIGHTS)
def test_k3_k4_choice_alternatives_stay_on_one_page(
    variant: ExamPrintVariant, filler_lines: int
) -> None:
    """K4: no break falls between two alternatives and no alternative splits."""
    rendered = _render(make_document(_filler(filler_lines), _choice_item()), variant)
    locations = [_pages_with(rendered, f"VAL{index}") for index in range(1, 7)]
    assert (
        all(len(found) == 1 for found in locations)
        and len({min(found) for found in locations}) == 1
    ), (
        f"N={filler_lines} {variant.value}: {len(rendered.pages)} pages, "
        f"alternatives={[sorted(found) for found in locations]}"
    )


def test_k3_text_may_stay_while_alternatives_move_to_the_next_page() -> None:
    """K3: where the text fits but the alternatives do not, the text stays behind."""
    observations = []
    for variant in VARIANTS:
        for filler_lines in HEIGHTS:
            rendered = _render(make_document(_filler(filler_lines), _choice_item()), variant)
            text = _pages_with(rendered, "VALTEXT")
            alternatives = [_pages_with(rendered, f"VAL{index}") for index in range(1, 7)]
            observations.append((variant, filler_lines, text, alternatives))
    assert any(
        len(_render(make_document(_filler(n), _choice_item()), variant).pages) >= 2
        for variant in VARIANTS
        for n in HEIGHTS
    ), "the sweep never reaches a second page"
    matches = [
        (variant, filler_lines)
        for variant, filler_lines, text, alternatives in observations
        if len(text) == 1
        and all(len(found) == 1 for found in alternatives)
        and min(text) < min(min(found) for found in alternatives)
    ]
    assert matches, (
        "no height keeps the text behind while all alternatives start the next page: "
        + ", ".join(
            f"{variant.value}/N={n}: text={sorted(text)} "
            f"alts={[sorted(found) for found in alternatives]}"
            for variant, n, text, alternatives in observations
        )
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("filler_lines", HEIGHTS)
def test_k5_k14_tall_question_splits_only_between_paragraphs(
    variant: ExamPrintVariant, filler_lines: int
) -> None:
    """K5/K14: taller-than-a-page text splits, never inside a paragraph."""
    tall = make_free_text_item(sequence=2, item_id="item_002")
    tall = tall.model_copy(
        update={
            "points": 4,
            "writing_lines": 1,
            "body": tuple(
                make_paragraph(" ".join([f"TALL{index:02d}"] * 120)) for index in range(40)
            ),
        }
    )
    rendered = _render(make_document(_filler(filler_lines), tall), variant)
    assert len(rendered.pages) > 1, (
        f"N={filler_lines} {variant.value}: the tall question fits on one page"
    )
    split = [(index, sorted(_pages_with(rendered, f"TALL{index:02d}"))) for index in range(40)]
    broken = [(index, pages) for index, pages in split if len(pages) > 1]
    assert not broken, (
        f"N={filler_lines} {variant.value}: {len(rendered.pages)} pages, "
        f"paragraphs split inside: {broken[:6]}"
    )


def _tall_gap_fill_item() -> NativeExamItem:
    """Eight ~70 mm gap-fill paragraphs, each with a unique marker and one gap."""
    paragraphs = tuple(
        NativeParagraph(
            heading_level=None,
            segments=(
                NativeTextSegment(text=" ".join([f"GAP{index:02d}"] * 65), marks=()),
                NativeGapSegment(gap_id=f"gap_{index + 1:03d}"),
            ),
        )
        for index in range(8)
    )
    gaps = tuple(
        NativeGap(gap_id=f"gap_{index + 1:03d}", accepted_values=("ja",)) for index in range(8)
    )
    return gap_fill_item(paragraphs, gaps, sequence=2, item_id="item_002")


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("filler_lines", HEIGHTS)
def test_k5_k14_tall_gap_fill_question_splits_only_between_paragraphs(
    variant: ExamPrintVariant, filler_lines: int
) -> None:
    """K5/K14: a taller-than-a-page gap-fill question never splits inside a paragraph."""
    document = make_document(_filler(filler_lines), _tall_gap_fill_item())
    html = render_print_html(
        build_print_document(document, variant=variant),
        assets=document.assets,
        assets_by_id={},
    )
    assert html.count('class="print-gap_line"') == 8, (
        "the fixture does not exercise gap-fill paragraphs"
    )
    rendered = _render(document, variant)
    assert len(rendered.pages) > 1, (
        f"N={filler_lines} {variant.value}: the tall gap-fill question fits on one page"
    )
    split = [(index, sorted(_pages_with(rendered, f"GAP{index:02d}"))) for index in range(8)]
    missing = [(index, pages) for index, pages in split if not pages]
    assert not missing, f"N={filler_lines} {variant.value}: markers missing: {missing}"
    broken = [(index, pages) for index, pages in split if len(pages) > 1]
    assert not broken, (
        f"N={filler_lines} {variant.value}: {len(rendered.pages)} pages, "
        f"gap-fill paragraphs split inside: {broken[:6]}"
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("filler_lines", HEIGHTS)
def test_k2_writing_lines_split_while_the_text_stays_whole(
    variant: ExamPrintVariant, filler_lines: int
) -> None:
    """K2: writing lines may split across pages; the question text never does."""
    case = make_free_text_item(sequence=2, item_id="item_002")
    case = case.model_copy(
        update={
            "points": 4,
            "writing_lines": 30,
            "body": (make_paragraph("Resonera om romantiken K2TEXT."),),
        }
    )
    rendered = _render(make_document(_filler(filler_lines), case), variant)
    text = _pages_with(rendered, "K2TEXT")
    lines = _line_pages(rendered)
    assert len(text) == 1, f"N={filler_lines} {variant.value}: the text splits: {sorted(text)}"
    assert len(lines) >= 2, (
        f"N={filler_lines} {variant.value}: the writing area fits on {sorted(lines)}"
    )


def _part_document(filler_lines: int) -> NativeExamDocument:
    child = make_free_text_item(sequence=2, item_id="item_002")
    child = child.model_copy(
        update={
            "points": 4,
            "writing_lines": 1,
            "body": (make_paragraph("Besvara frågan K12BARN."),),
        }
    )
    parent = NativeExamParent(
        parent_id="parent_001",
        place=1,
        instruction=(make_paragraph("Läs texten noga K12INSTR."),),
        item_ids=("item_002",),
    )
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(_filler(filler_lines), child),
        parents=(parent,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("filler_lines", HEIGHTS)
def test_k12_part_instruction_stays_with_its_first_question(
    variant: ExamPrintVariant, filler_lines: int
) -> None:
    """K12: a part's instruction stays on the same page as its first question."""
    rendered = _render(_part_document(filler_lines), variant)
    instruction = _pages_with(rendered, "K12INSTR")
    heading = _pages_with(rendered, "Fråga 2")
    assert instruction == heading and len(heading) == 1, (
        f"N={filler_lines} {variant.value}: {len(rendered.pages)} pages, "
        f"instruction={sorted(instruction)} heading={sorted(heading)}"
    )


def test_k12_sweep_reaches_a_page_end() -> None:
    """The K12 sweep proves something: some height pushes the pair onto page 2+."""
    starts = [
        min(_pages_with(_render(_part_document(n), variant), "Fråga 2"))
        for variant in VARIANTS
        for n in HEIGHTS
    ]
    assert any(page >= 2 for page in starts), f"no height reached page 2: {starts}"


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("filler_lines", HEIGHTS)
def test_k15_ordering_steps_stay_on_one_page(variant: ExamPrintVariant, filler_lines: int) -> None:
    """K15: all ordering steps lay out on one page."""
    steps = tuple(f"Steg ORD{index} i ordningen" for index in range(1, 7))
    case = make_ordering_item(sequence=2, item_id="item_002", steps=steps)
    rendered = _render(make_document(_filler(filler_lines), case), variant)
    locations = [_pages_with(rendered, f"ORD{index}") for index in range(1, 7)]
    assert (
        all(len(found) == 1 for found in locations)
        and len({min(found) for found in locations}) == 1
    ), (
        f"N={filler_lines} {variant.value}: {len(rendered.pages)} pages, "
        f"steps={[sorted(found) for found in locations]}"
    )


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("filler_lines", HEIGHTS)
def test_k15_matching_grid_stays_on_one_page(variant: ExamPrintVariant, filler_lines: int) -> None:
    """K15: the whole matching grid lays out on one page."""
    rendered = _render(make_document(_filler(filler_lines), _matching_item()), variant)
    locations = [_pages_with(rendered, f"MATCHL{index}") for index in range(1, 5)]
    assert (
        all(len(found) == 1 for found in locations)
        and len({min(found) for found in locations}) == 1
    ), (
        f"N={filler_lines} {variant.value}: {len(rendered.pages)} pages, "
        f"rows={[sorted(found) for found in locations]}"
    )


def test_k15_sweep_reaches_a_page_end() -> None:
    """The K15 sweep proves something: some height pushes each grid onto page 2+."""
    starts = [
        (
            min(_pages_with(_render(make_document(_filler(n), case()), variant), marker)),
            variant,
            n,
        )
        for case, marker in (
            (
                lambda: make_ordering_item(
                    sequence=2,
                    item_id="item_002",
                    steps=tuple(f"Steg ORD{index} i ordningen" for index in range(1, 7)),
                ),
                "ORD1",
            ),
            (_matching_item, "MATCHL1"),
        )
        for variant in VARIANTS
        for n in HEIGHTS
    ]
    assert any(page >= 2 for page, _, _ in starts), f"no height reached page 2: {starts}"
