"""Header metadata follows source anchors, not item position or question-id spelling."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_header import apply_header
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


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Total: 36 poäng", 36),
        ("Totalt 40 p", 40),
        ("Poäng: 15 poäng", 15),
        ("Max 36p", 36),
        ("36 poäng totalt", 36),
        ("Totalt: 7,5 p", 7.5),
        ("Totalt: 7.5 p", 7.5),
        ("Del 2: 15 poäng", 15),
        ("Totalpoäng saknas", None),
    ],
)
def test_printed_exam_total_reads_the_points_not_an_earlier_part_number(
    line: str, expected: int | float | None
) -> None:
    result = apply_header(
        _document(),
        _manifest((HeaderAnchor("h1", "exam_total", ()),)),
        (_chunk("h1", line),),
        course_key=None,
        courses=(),
    )
    assert result.header.printed_total == expected


def test_course_lines_keep_plain_source_order_and_first_parsable_exam_total() -> None:
    result = apply_header(
        _document(),
        _manifest(
            (
                HeaderAnchor("c2", "course", ()),
                HeaderAnchor("t3", "exam_total", ()),
                HeaderAnchor("c1", "course", ()),
                HeaderAnchor("t2", "exam_total", ()),
                HeaderAnchor("t1", "exam_total", ()),
            )
        ),
        (
            _chunk("c1", "Svenska 2", marked="**Svenska** <i>2</i>"),
            _chunk("c2", "Kursavslutande", marked="<u>Kursavslutande</u>"),
            _chunk("t1", "Total saknas"),
            _chunk("t2", "Total: 36 poäng"),
            _chunk("t3", "Total: 99 poäng"),
        ),
        course_key=None,
        courses=(),
    )
    assert result.header.course_hint == "Svenska 2 Kursavslutande"
    assert result.header.printed_total == 36
    assert result.instructions == ()


def test_empty_course_line_has_no_hint() -> None:
    result = apply_header(
        _document(),
        _manifest((HeaderAnchor("c1", "course", ()),)),
        (_chunk("c1", "   "),),
        course_key=None,
        courses=(),
    )
    assert result.header.course_hint is None


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
    assert [parent.printed_total for parent in result.parents] == [None, 15]
    assert [item.points for item in result.items] == [1, 1, 1, 1, 1]


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
    assert [parent.printed_total for parent in result.parents] == [None, 40]


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
    assert result.parents[0].printed_total == 15
    assert result.items[0].points == 1


@pytest.mark.parametrize("existing_points", [None, 3, 7.5])
def test_single_unparented_question_takes_missing_points_or_gets_nonblocking_reason(
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
    assert result.parents == ()
    assert result.items[0].points == (7.5 if existing_points is None else existing_points)
    assert result.items[0].review.state == item.review.state
    if existing_points == 3:
        assert "Tryckt delsumma 7,5 p, frågan har 3 p" in result.items[0].review.reasons
    else:
        assert result.items[0].review.reasons == item.review.reasons
