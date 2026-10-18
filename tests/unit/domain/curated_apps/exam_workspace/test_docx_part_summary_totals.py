"""Part totals printed in a one-line summary of several parts, and the one owner of a
one-question part line (TASK-SKRIPT-39-04-12 review-2 F1, exempelprov ruling point 2)."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
    SharedContext,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_labels import part_totals
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    PrintedPoints,
    assign_points_lines,
    printed_points_plan,
)

pytestmark = pytest.mark.unit

# Exempelprov grammatik sve2 v2.1, body:0010.
_SUMMARY = (
    "Del 1: Morfem och fraser (20 p) • Del 2: Satslösning (20 p) • "
    "Del 3: Bisatser (15 p) • Del 4: Textanalys (15 p)"
)

_P = "paragraph"
_H = "heading"


def _plan(
    lines: tuple[tuple[str, str], ...], questions: tuple[tuple[int, ...], ...]
) -> tuple[tuple[DocxChunk, ...], PrintedPoints]:
    chunks = tuple(
        DocxChunk(f"a{index}", kind, text, text) for index, (kind, text) in enumerate(lines)
    )
    grouped = tuple(tuple(chunks[i].anchor for i in own) for own in questions)
    return chunks, printed_points_plan(chunks, grouped)


def test_a_summary_line_gives_each_part_its_total():
    assert part_totals(_SUMMARY) == (("1", 20), ("2", 20), ("3", 15), ("4", 15))


@pytest.mark.parametrize(
    "text",
    ["Del 1: Morfem och fraser (20 p)", "Poängöversikt: 70 p", "Del 1 och Del 2 handlar om ord"],
    ids=["one_part", "no_part", "no_totals"],
)
def test_a_line_without_two_part_totals_is_no_summary(text: str):
    assert part_totals(text) == ()


def test_a_part_segment_with_two_labels_prints_no_total():
    assert part_totals("Del 1: 4 p eller 6 p • Del 2: 5 p • Del 3: 7 p") == (("2", 5), ("3", 7))


# Four part headings that print no total of their own, under the exempelprov summary.
_EXEMPELPROV = (
    (_P, _SUMMARY),
    (_P, "Totalt: 70 poäng"),
    (_H, "DEL 1: MORFEM OCH FRASER"),
    (_H, "Uppgift 1.1: Morfemanalys"),
    (_H, "Uppgift 1.2: Fraser"),
    (_H, "DEL 2: SATSLÖSNING"),
    (_H, "Uppgift 2.1: Enkel satslösning"),
    (_H, "DEL 3: BISATSER"),
    (_H, "Uppgift 3.1: Bisatstyp"),
    (_H, "DEL 4: TEXTANALYS"),
    (_H, "Uppgift 4.1: Jämför texterna"),
)
_EXEMPELPROV_QUESTIONS = ((3,), (4,), (6,), (8,), (10,))


def test_a_summary_line_opens_each_part_its_heading_names():
    chunks, plan = _plan(_EXEMPELPROV, _EXEMPELPROV_QUESTIONS)

    assert [(p.identity, p.total, p.questions, p.opener) for p in plan.parts] == [
        ("1", 20, (0, 1), "a2"),
        ("2", 20, (2,), "a5"),
        ("3", 15, (3,), "a7"),
        ("4", 15, (4,), "a9"),
    ]
    assert chunks[0].anchor in plan.metadata
    # The summary is no exam-total candidate and no question's line.
    assert plan.exam_total == 70
    assert chunks[0].anchor not in plan.owners
    assert not [q for q in plan.questions if q.prints]


def test_a_part_heading_that_prints_another_total_than_the_summary_opens_no_part():
    lines = tuple(
        (_H, "DEL 2: SATSLÖSNING (18 p)") if text == "DEL 2: SATSLÖSNING" else (kind, text)
        for kind, text in _EXEMPELPROV
    )

    _, plan = _plan(lines, _EXEMPELPROV_QUESTIONS)

    assert [(p.identity, p.total) for p in plan.parts] == [("1", 20), ("3", 15), ("4", 15)]
    # Its question stays outside every part rather than joining part 1.
    assert plan.parts[0].questions == (0, 1)


def test_a_part_heading_that_prints_the_summary_total_opens_its_part():
    lines = tuple(
        (_H, "DEL 2: SATSLÖSNING (20 p)") if text == "DEL 2: SATSLÖSNING" else (kind, text)
        for kind, text in _EXEMPELPROV
    )

    _, plan = _plan(lines, _EXEMPELPROV_QUESTIONS)

    assert [(p.identity, p.total) for p in plan.parts] == [
        ("1", 20),
        ("2", 20),
        ("3", 15),
        ("4", 15),
    ]


def test_a_summary_line_inside_a_question_span_is_that_questions_text():
    lines = (
        (_H, "Uppgift 1: Läs översikten"),
        (_P, _SUMMARY),
        (_H, "DEL 1: MORFEM"),
        (_H, "Uppgift 2: Morfemanalys"),
    )

    chunks, plan = _plan(lines, ((0, 1), (3,)))

    assert plan.parts == ()
    assert chunks[1].anchor not in plan.metadata


def test_a_one_question_part_line_joins_its_question_wherever_the_grouping_put_it():
    # Review-2 F1: the grouping gives q2's heading to q1 and its key; the normalised manifest
    # holds it as q2's alone, so every consumer reads one owner.
    texts = (
        (_P, "Förklara vad som kännetecknar ett substantiv. (4 p)"),
        (_H, "Uppgift 2: Verb (2 p)"),
        (_P, "Förklara vad som kännetecknar ett verb."),
    )
    chunks = tuple(DocxChunk(f"a{i}", kind, text, text) for i, (kind, text) in enumerate(texts))
    manifest = ExamManifest(
        questions=(
            ManifestQuestion("q1", ("a0", "a1"), ("a1",), ("a1",)),
            ManifestQuestion("q2", ("a2",), (), ()),
        ),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )

    q1, q2 = assign_points_lines(manifest, chunks).questions

    assert (q1.anchors, q1.subpart_anchors, q1.key_anchors) == (("a0",), (), ())
    assert q2.anchors == ("a1", "a2")


def test_a_summary_opened_part_heading_over_one_question_is_unplaced_and_never_starts_it():
    chunks = tuple(
        DocxChunk(f"a{i}", kind, text, text) for i, (kind, text) in enumerate(_EXEMPELPROV)
    )
    # The grouping puts DEL 2 in its question's anchors and DEL 4 in its key and context.
    grouped = ((3,), (4,), (5, 6), (8,), (10,))
    manifest = ExamManifest(
        questions=tuple(
            ManifestQuestion(
                f"q{n + 1}",
                tuple(chunks[i].anchor for i in own),
                (),
                ("a9",) if n == 4 else (),
            )
            for n, own in enumerate(grouped)
        ),
        contexts=(SharedContext(anchor="a9", scope="section_instruction", owner="q5", governs=()),),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=("a0", "a1", "a2", "a7"),
    )

    result = assign_points_lines(manifest, chunks)

    # A part-labelled line is never a question anchor, whatever number of questions its part
    # holds: it leaves every placement and is unplaced section structure.
    assert [q.anchors for q in result.questions] == [("a3",), ("a4",), ("a6",), ("a8",), ("a10",)]
    assert [q.key_anchors for q in result.questions] == [()] * 5
    assert result.contexts == ()
    assert result.unplaced_anchors == ("a0", "a1", "a2", "a5", "a7", "a9")
    # Planned again over the normalised questions, every part keeps its questions and total.
    again = printed_points_plan(chunks, tuple(q.anchors for q in result.questions))
    assert [(p.identity, p.total, p.questions) for p in again.parts] == [
        ("1", 20, (0, 1)),
        ("2", 20, (2,)),
        ("3", 15, (3,)),
        ("4", 15, (4,)),
    ]


# Parts nest (parent rule (ii), 2026-10-18): a part-labelled line is an outer part that runs
# to the next part-labelled line; a part line with no part label is an inner part that runs
# to the next part line of either kind. Question spans end at every part line.


def _parts(plan: PrintedPoints) -> list[tuple[str | None, int | float, tuple[int, ...], str]]:
    return [(p.identity, p.total, p.questions, p.opener) for p in plan.parts]


# Exempelprov grammatik sve2 v2.1: part headings print no total; the summary totals them, and
# every question heading prints the question's own total with a closing "/n p" line.
_NESTED_EXEMPELPROV = (
    (_P, _SUMMARY),
    (_P, "Totalt: 70 poäng"),
    (_H, "DEL 1: MORFEM OCH FRASER"),
    (_H, "Uppgift 1.1: Morfemanalys (4 p)"),
    (_P, "Dela upp orden i morfem."),
    (_P, "/4 p"),
    (_H, "Uppgift 1.2: Identifiera fraser i texten (16 p)"),
    (_P, "Läs texten nedan."),
    (_P, "/16 p"),
    (_H, "DEL 2: SATSLÖSNING"),
    (_H, "Uppgift 2.1: Enkel satslösning (20 p)"),
    (_P, "Gör satsdelsanalys."),
    (_P, "/20 p"),
    (_H, "DEL 3: BISATSER"),
    (_H, "Uppgift 3.1: Bestäm bisatstyp (9 p)"),
    (_P, "Stryk under bisatsen."),
    (_H, "Uppgift 3.2: Analysera komplex mening (6 p)"),
    (_P, "Analysera meningen."),
    (_H, "DEL 4: TEXTANALYS – SPRÅKLIGA DRAG"),
    (_H, "Uppgift 4.1: Jämför texterna (15 p)"),
    (_P, "Läs de två texterna."),
    (_P, "/15 p"),
)
_NESTED_QUESTIONS = ((3, 4, 5), (6, 7, 8), (10, 11, 12), (14, 15), (16, 17), (19, 20, 21))


def test_part_headings_hold_the_questions_under_their_numbered_headings():
    chunks, plan = _plan(_NESTED_EXEMPELPROV, _NESTED_QUESTIONS)

    assert _parts(plan) == [
        ("1", 20, (0, 1), "a2"),
        (None, 4, (0,), "a3"),
        (None, 16, (1,), "a6"),
        ("2", 20, (2,), "a9"),
        (None, 20, (2,), "a10"),
        ("3", 15, (3, 4), "a13"),
        (None, 9, (3,), "a14"),
        (None, 6, (4,), "a16"),
        ("4", 15, (5,), "a18"),
        (None, 15, (5,), "a19"),
    ]
    # Each "/n p" line closes its question's inner part; none is a question's own line.
    assert plan.owners == {}
    assert not [q for q in plan.questions if q.prints]
    assert plan.exam_total == 70


def test_a_part_heading_over_several_questions_is_a_section_and_numbered_headings_join():
    chunks = tuple(
        DocxChunk(f"a{i}", kind, text, text) for i, (kind, text) in enumerate(_NESTED_EXEMPELPROV)
    )
    # The grouping puts DEL 1 in its first question and DEL 4 in its one question.
    grouped = ((2, *_NESTED_QUESTIONS[0]), *_NESTED_QUESTIONS[1:5], (18, *_NESTED_QUESTIONS[5]))
    manifest = ExamManifest(
        questions=tuple(
            ManifestQuestion(f"q{n + 1}", tuple(chunks[i].anchor for i in own), (), ())
            for n, own in enumerate(grouped)
        ),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=("a0", "a1", "a9", "a13"),
    )

    result = assign_points_lines(manifest, chunks)

    # Every part-labelled line leaves every question, whether its part holds several (DEL 1,
    # DEL 3) or one (DEL 2, DEL 4): it is unplaced section structure. Numbered headings join.
    assert result.unplaced_anchors == (
        "a0", "a1", "a2", "a5", "a8", "a9", "a12", "a13", "a18", "a21",
    )  # fmt: skip
    assert [q.anchors for q in result.questions] == [
        ("a3", "a4"),
        ("a6", "a7"),
        ("a10", "a11"),
        ("a14", "a15"),
        ("a16", "a17"),
        ("a19", "a20"),
    ]


def test_a_part_heading_with_a_total_holds_the_numbered_questions_under_it():
    lines = (
        (_H, "Del 2: 15 poäng"),
        (_H, "1. Tempus (5 p)"),
        (_P, "Böj verben."),
        (_H, "2. Modus (10 p)"),
        (_P, "Förklara modus."),
    )

    _, plan = _plan(lines, ((1, 2), (3, 4)))

    assert _parts(plan) == [
        ("2", 15, (0, 1), "a0"),
        (None, 5, (0,), "a1"),
        (None, 10, (1,), "a3"),
    ]


_TWO_PART_SUMMARY = "Del 1: Ord (10 p) • Del 2: Satser (20 p)"


def test_a_part_heading_whose_total_differs_from_the_summary_opens_no_part_but_ends_spans():
    lines = (
        (_P, _TWO_PART_SUMMARY),
        (_H, "Del 1: Ord (10 p)"),
        (_H, "1. Ordklasser (4 p)"),
        (_P, "Ange ordklass."),
        (_H, "2. Böjning (6 p)"),
        (_P, "Böj orden."),
        (_H, "Del 2: Satser (18 p)"),
        (_P, "/6 p"),
        (_H, "3. Satsdelar (20 p)"),
        (_P, "Ange satsdelar."),
    )

    chunks, plan = _plan(lines, ((2, 3), (4, 5), (8, 9)))

    # D3: part 2 prints 18 and the summary 20, so it opens no part, yet it ends part 1.
    assert _parts(plan) == [
        ("1", 10, (0, 1), "a1"),
        (None, 4, (0,), "a2"),
        (None, 6, (1,), "a4"),
        (None, 20, (2,), "a8"),
    ]
    # The line after it lies in no question's span.
    assert chunks[7].anchor not in plan.owners
    assert not plan.questions[1].prints


def test_a_points_line_printing_the_part_total_closes_the_outer_part():
    lines = (
        (_H, "Del 1: Ord (10 p)"),
        (_H, "1. Ordklasser (4 p)"),
        (_P, "Ange ordklass."),
        (_H, "2. Böjning (6 p)"),
        (_P, "Böj orden."),
        (_P, "/10 p"),
        (_H, "Del 2: Satser (5 p)"),
        (_H, "3. Satsdelar (5 p)"),
        (_P, "Ange satsdelar."),
    )

    chunks, plan = _plan(lines, ((1, 2), (3, 4), (7, 8)))

    assert _parts(plan)[0] == ("1", 10, (0, 1), "a0")
    # "/10 p" is part 1's line: neither question 2's own line nor any question's points.
    assert chunks[5].anchor not in plan.owners
    assert chunks[5].anchor in plan.metadata
    assert not plan.questions[1].prints


# Omprov grammatik sve2: the same summary, but the part lines are Word paragraphs.
_PARAGRAPH_PARTS = tuple(
    (_P, text) if text.startswith("DEL ") else (kind, text) for kind, text in _EXEMPELPROV
)


def test_a_part_paragraph_a_summary_names_opens_its_part_with_the_summary_total():
    chunks, plan = _plan(_PARAGRAPH_PARTS, _EXEMPELPROV_QUESTIONS)

    assert _parts(plan) == [
        ("1", 20, (0, 1), "a2"),
        ("2", 20, (2,), "a5"),
        ("3", 15, (3,), "a7"),
        ("4", 15, (4,), "a9"),
    ]
    assert chunks[0].anchor in plan.metadata
    assert plan.exam_total == 70


def test_a_part_paragraph_no_summary_names_opens_nothing():
    lines = (
        (_P, "Del 1: Ord (10 p) • Del 2: Satser (20 p)"),
        (_P, "DEL 3: BISATSER"),
        (_H, "Uppgift 1: Bisatstyp"),
        (_P, "Ange bisatstyp."),
    )

    _, plan = _plan(lines, ((2, 3),))

    assert plan.parts == ()


def test_a_part_labelled_prose_sentence_with_several_totals_opens_no_part():
    lines = (
        (_P, _TWO_PART_SUMMARY),
        (_P, "Del 1 ger 4 p för rätt ordklass och 6 p för rätt böjning i varje rad."),
        (_H, "Uppgift 1: Ordklasser"),
        (_P, "Ange ordklass."),
    )

    _, plan = _plan(lines, ((2, 3),))

    assert plan.parts == ()
