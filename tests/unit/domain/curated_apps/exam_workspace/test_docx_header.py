"""Header metadata follows source anchors, not item position or question-id spelling."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_header import apply_header
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    HeaderAnchor,
    ManifestQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    manifest_questions,
    printed_points_plan,
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


_Q12 = _manifest((), (_question("q1", "q1"), _question("q2", "q2")))


@pytest.mark.parametrize(
    ("chunks", "expected"),
    [
        ((_chunk("t", "Total: 36 poäng"), _chunk("q1", "1. Fråga")), 36),
        ((_chunk("n", "Namn:"), _chunk("q1", "1. Fråga")), None),
        # Two totals that differ are no exam total, in either order and with or without a
        # part line between them and the first question (D3, R2-1).
        ((_chunk("a", "Total: 36 poäng"), _chunk("b", "Max 40 p"), _chunk("q1", "1.")), None),
        ((_chunk("a", "Total: 36 poäng"), _chunk("b", "Totalt 40 p"), _chunk("q1", "1.")), None),
        ((_chunk("b", "Totalt 40 p"), _chunk("a", "Total: 36 poäng"), _chunk("q1", "1.")), None),
        (
            (
                _chunk("a", "Total: 36 poäng"),
                _chunk("b", "Max 40 p"),
                _heading("h", "Del 1: 15 poäng"),
                _chunk("q1", "1."),
            ),
            None,
        ),
        (
            (_chunk("a", "Total: 36 poäng"), _chunk("b", "Max 36p"), _chunk("q1", "1.")),
            36,
        ),
        ((_chunk("q1", "1. Fråga"), _chunk("t", "Total: 36 poäng")), None),
        # A line opening the first section is never the exam total, heading or paragraph.
        (
            (_chunk("t", "Total: 36 poäng"), _heading("h", "Del 1: 15 poäng"), _chunk("q1", "1.")),
            36,
        ),
        (
            (_chunk("t", "Total: 36 poäng"), _chunk("d", "Del 1: 15 poäng"), _chunk("q1", "1.")),
            36,
        ),
        # A heading can print the exam total.
        ((_heading("h", "Total: 36 poäng"), _chunk("q1", "1. Fråga")), 36),
        ((_heading("h", "Prov i svenska, 40 poäng"), _chunk("q1", "1. Fråga")), 40),
        # A part label opens a part, heading or paragraph; it is never the exam total.
        (
            (
                _chunk("d", "Del 1: 15 poäng"),
                _chunk("q1", "1."),
                _chunk("d2", "Del 2: 21 poäng"),
                _chunk("q2", "2."),
            ),
            None,
        ),
        (
            (
                _heading("h1", "Del 1: 15 poäng"),
                _chunk("q1", "1."),
                _heading("h2", "Del 2: 21 poäng"),
                _chunk("q2", "2."),
            ),
            None,
        ),
        # The sa24 shape: a plain total before q1; later parts open with headings.
        (
            (
                _chunk("t", "Total: 74 points"),
                _chunk("q1", "1."),
                _heading("h", "E Choose the words (15 points)"),
                _chunk("q2", "2."),
            ),
            74,
        ),
        # The Svenska 2 shape: total, part heading, questions, a closing line, next part.
        (
            (
                _chunk("t", "Total: 36 poäng"),
                _heading("h1", "Del 1: litteraturhistoria, 15 poäng"),
                _chunk("q1", "1."),
                _chunk("c", "Poäng: 15 poäng"),
                _heading("h2", "Del 2: grammatik, 21 poäng"),
                _chunk("q2", "2."),
            ),
            36,
        ),
        ((_chunk("t", "Total: 36,5 poäng"), _chunk("q1", "1. Fråga")), 36.5),
        ((_chunk("t", "Del 1: 15 poäng, del 2: 21 poäng"), _chunk("q1", "1.")), None),
    ],
)
def test_printed_exam_total_is_the_one_total_line_before_the_first_question(
    chunks: tuple[DocxChunk, ...], expected: int | float | None
) -> None:
    assert printed_points_plan(chunks, manifest_questions(_Q12)).exam_total == expected


def test_paragraph_part_lines_each_open_their_part() -> None:
    chunks = (
        _chunk("d", "Del 1: 15 poäng"),
        _chunk("q1", "1."),
        _chunk("d2", "Del 2: 21 poäng"),
        _chunk("q2", "2."),
    )

    plan = printed_points_plan(chunks, manifest_questions(_Q12))

    assert plan.exam_total is None
    assert [(part.total, part.questions) for part in plan.parts] == [(15, (0,)), (21, (1,))]
    assert plan.metadata == {"d", "d2"}
    assert not plan.owners


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


@pytest.mark.parametrize("own", [("b",), ("h", "b")], ids=["body-only", "heading-in-own-anchors"])
def test_an_exam_total_heading_stays_the_exams_wherever_the_grouping_places_it(
    own: tuple[str, ...],
) -> None:
    """R3-2: a question owning the total heading does not turn it into question text."""
    chunks = (
        DocxChunk("h", "heading", "Total: 36 poäng", "Total: 36 poäng"),
        DocxChunk("b", "paragraph", "1. Förklara.", "1. Förklara."),
    )

    assert printed_points_plan(chunks, (own,)).exam_total == 36
