"""Header metadata follows source anchors, not item position or question-id spelling."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_header import (
    apply_header,
    printed_exam_total,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    HeaderAnchor,
    ManifestQuestion,
    SharedContext,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    choice,
    conversion_update,
)


def _chunk(anchor: str, text: str, *, marked: str | None = None) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind="paragraph", text=text, marked_text=marked or text)


def _manifest(
    headers: tuple[HeaderAnchor, ...],
    questions: tuple[ManifestQuestion, ...] = (),
) -> ExamManifest:
    return ExamManifest(
        questions=questions,
        contexts=(),
        title_anchors=(),
        header=headers,
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )


def _question(qid: str, *anchors: str) -> ManifestQuestion:
    return ManifestQuestion(question_id=qid, anchors=anchors, subpart_anchors=(), key_anchors=())


def _document() -> NativeExamDocument:
    return conversion_update([("q1", [choice("p1", "Frågan")])], pending=()).document


def _heading(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor=anchor, kind="heading", text=text, marked_text=text)


_Q1 = _manifest((), (_question("q1", "q1"),))


@pytest.mark.parametrize(
    ("chunks", "expected"),
    [
        ((_chunk("t", "Total: 36 poäng"), _chunk("q1", "1. Fråga")), 36),
        ((_chunk("n", "Namn:"), _chunk("q1", "1. Fråga")), None),
        (
            (_chunk("a", "Total: 36 poäng"), _chunk("b", "Totalt 40 p"), _chunk("q1", "1.")),
            None,
        ),
        (
            (_chunk("a", "Total: 36 poäng"), _chunk("b", "Max 36p"), _chunk("q1", "1.")),
            36,
        ),
        ((_chunk("q1", "1. Fråga"), _chunk("t", "Total: 36 poäng")), None),
        (
            (_heading("h", "Del 1: 15 poäng"), _chunk("t", "Total: 36 poäng"), _chunk("q1", "1.")),
            36,
        ),
        ((_heading("h", "Total: 36 poäng"), _chunk("q1", "1. Fråga")), None),
        ((_chunk("t", "Total: 36,5 poäng"), _chunk("q1", "1. Fråga")), 36.5),
        ((_chunk("t", "Del 1: 15 poäng, del 2: 21 poäng"), _chunk("q1", "1.")), None),
    ],
)
def test_printed_exam_total_is_the_one_total_line_before_the_first_question(
    chunks: tuple[DocxChunk, ...], expected: int | float | None
) -> None:
    assert printed_exam_total(chunks, _Q1) == expected


def test_apply_header_takes_the_exam_total_from_the_text_without_a_header_anchor() -> None:
    result = apply_header(
        _document(),
        _Q1,
        (_chunk("t", "Total: 36 poäng"), _chunk("q1", "Frågan")),
        course_key=None,
        courses=(),
    )
    assert result.document.header.printed_total == 36


def test_course_lines_keep_plain_source_order() -> None:
    result = apply_header(
        _document(),
        _manifest((HeaderAnchor("c2", "course", ()), HeaderAnchor("c1", "course", ()))),
        (
            _chunk("c1", "Svenska 2", marked="**Svenska** <i>2</i>"),
            _chunk("c2", "Kursavslutande", marked="<u>Kursavslutande</u>"),
        ),
        course_key=None,
        courses=(),
    )
    assert result.document.header.course_hint == "Svenska 2 Kursavslutande"
    assert result.document.instructions == ()


def test_empty_course_line_has_no_hint() -> None:
    result = apply_header(
        _document(),
        _manifest((HeaderAnchor("c1", "course", ()),)),
        (_chunk("c1", "   "),),
        course_key=None,
        courses=(),
    )
    assert result.document.header.course_hint is None


def test_part_totals_follow_source_ownership_into_adjacent_parents() -> None:
    document = conversion_update(
        [
            ("q1", [choice("p1", "Ett")]),
            ("q2", [choice("p2", "Två")]),
            ("q21", [choice("p21a", "Tjugoett a"), choice("p21b", "Tjugoett b")]),
            ("q22", [choice("p22", "Tjugotvå")]),
        ],
        pending=(),
        parents=(("left", ("q1", "q2")), ("right", ("q21", "q22"))),
    ).document
    result = apply_header(
        document,
        _manifest(
            (HeaderAnchor("h2", "part_total", ("q21", "q22")),),
            (
                _question("q1", "p1"),
                _question("q2", "p2"),
                _question("q21", "p21a", "p21b"),
                _question("q22", "p22"),
            ),
        ),
        (
            _chunk("p1", "Ett"),
            _chunk("p2", "Två"),
            _chunk("h2", "Del 2: 15 poäng"),
            _chunk("p21a", "Tjugoett a"),
            _chunk("p21b", "Tjugoett b"),
            _chunk("p22", "Tjugotvå"),
        ),
        course_key=None,
        courses=(),
    )
    assert [parent.printed_total for parent in result.document.parents] == [None, 15]
    assert [item.points for item in result.document.items] == [1, 1, 1, 1, 1]


def test_part_total_uses_largest_overlap_even_when_some_questions_are_unparented() -> None:
    document = conversion_update(
        [(f"q{i}", [choice(f"p{i}", f"Fråga {i}")]) for i in range(1, 7)],
        pending=(),
        parents=(("left", ("q1", "q2")), ("right", ("q3", "q4", "q5"))),
    ).document
    result = apply_header(
        document,
        _manifest(
            (HeaderAnchor("h", "part_total", ("q2", "q3", "q4", "q6")),),
            tuple(_question(f"q{i}", f"p{i}") for i in range(1, 7)),
        ),
        (_chunk("h", "Totalt 40 p"), *(_chunk(f"p{i}", f"Fråga {i}") for i in range(1, 7))),
        course_key=None,
        courses=(),
    )
    assert [parent.printed_total for parent in result.document.parents] == [None, 40]


def test_part_total_uses_the_same_owned_context_mapping_as_pipeline_assembly() -> None:
    document = conversion_update(
        [("q1", [choice("c1", "Ett")]), ("q2", [choice("p2", "Två")])],
        pending=(),
        parents=(("part", ("q1", "q2")),),
    ).document
    manifest = _manifest(
        (HeaderAnchor("h", "part_total", ("q1",)),),
        (_question("q1", "p1"), _question("q2", "p2")),
    )
    manifest = ExamManifest(
        questions=manifest.questions,
        contexts=(SharedContext("c1", "section_instruction", "q1", ("q1",)),),
        title_anchors=(),
        header=manifest.header,
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    result = apply_header(
        document,
        manifest,
        (
            _chunk("h", "Poäng: 15 poäng"),
            _chunk("c1", "Läs texten och svara."),
            _chunk("p1", "Ett"),
            _chunk("p2", "Två"),
        ),
        course_key=None,
        courses=(),
    )
    assert result.document.parents[0].printed_total is None
    assert result.document.items[0].points == 15
    assert result.document.items[1].points == 1


@pytest.mark.parametrize("existing_points", [None, 3, 7.5])
def test_single_unparented_question_owns_its_printed_points(
    existing_points: int | float | None,
) -> None:
    document = _document()
    item = document.items[0].model_copy(update={"points": existing_points})
    document = document.model_copy(update={"items": (item,)})
    result = apply_header(
        document,
        _manifest((HeaderAnchor("h", "part_total", ("q1",)),), (_question("q1", "p1"),)),
        (_chunk("h", "Totalt 7,5 p"), _chunk("p1", "Frågan")),
        course_key=None,
        courses=(),
    )
    assert result.document.parents == ()
    assert result.document.items[0].points == 7.5
    assert result.document.items[0].review == item.review
