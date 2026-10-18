"""A part-labelled paragraph with one total opens its part; prose rates print none (D10a)."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    PrintedPart,
    assign_points_lines,
    printed_points_plan,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    corpus_chunks,
    recording,
)

pytestmark = pytest.mark.unit

_ENGLISH_1 = "bf26_english_1_unit_test_kap_1_2_med_facit"
# english_1's two prose sentences that print a rate: the vocabulary lead-in and
# "Each correct match is worth 1 point."
_RATE_SENTENCES = ("body:0006", "body:0058")


def _chunks(*lines: tuple[str, str]) -> tuple[DocxChunk, ...]:
    return tuple(
        DocxChunk(f"body:{index + 1:04d}", kind, text, text)
        for index, (kind, text) in enumerate(lines)
    )


def _manifest(chunks: tuple[DocxChunk, ...], grouped: tuple[tuple[int, ...], ...]) -> ExamManifest:
    return ExamManifest(
        questions=tuple(
            ManifestQuestion(f"q{number + 1}", tuple(chunks[i].anchor for i in own), (), ())
            for number, own in enumerate(grouped)
        ),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )


_LONG_TITLE = _chunks(
    ("paragraph", "Del 1: Ordklasser och ordbildning i svenska språket (6 p)"),
    ("paragraph", "1. Förklara vad ett substantiv är."),
    ("paragraph", "2. Förklara vad ett adjektiv är."),
)


@pytest.mark.parametrize("grouped", [((0, 1), (2,)), ((1,), (2,))], ids=["in_q1", "in_none"])
def test_a_long_titled_part_paragraph_opens_its_part_and_is_no_question_anchor(
    grouped: tuple[tuple[int, ...], ...],
) -> None:
    manifest = _manifest(_LONG_TITLE, grouped)
    opener = _LONG_TITLE[0].anchor

    normalised = assign_points_lines(manifest, _LONG_TITLE)
    plan = printed_points_plan(_LONG_TITLE, tuple(q.anchors for q in normalised.questions))

    assert plan.parts == (PrintedPart(6, (0, 1), opener, "1"),)
    assert [q.anchors for q in normalised.questions] == [("body:0002",), ("body:0003",)]
    assert opener in normalised.unplaced_anchors
    assert opener not in plan.owners
    assert plan.exam_total is None
    assert [q.prints for q in plan.questions] == [False, False]


@pytest.mark.parametrize("kind", ["paragraph", "heading"])
def test_a_short_part_line_opens_its_part_and_is_never_metadata(kind: str) -> None:
    # N3b requirement 2: "DEL 1 (6 p)" is also a points line, yet as a part opener it is
    # section structure, never metadata: placement must see its text.
    chunks = _chunks(
        (kind, "DEL 1 (6 p)"),
        ("paragraph", "1. Förklara vad ett substantiv är."),
        ("paragraph", "2. Förklara vad ett adjektiv är."),
    )

    plan = printed_points_plan(chunks, (("body:0002",), ("body:0003",)))

    assert plan.parts == (PrintedPart(6, (0, 1), "body:0001", "1"),)
    assert "body:0001" not in plan.metadata
    assert "body:0001" not in plan.owners


def test_a_part_labelled_paragraph_printing_two_totals_is_only_a_summary_candidate() -> None:
    chunks = _chunks(
        ("paragraph", "Del 1: Ordklasser (6 p) och Del 2: Satsdelar (4 p)"),
        ("paragraph", "1. Förklara vad ett substantiv är."),
        ("paragraph", "2. Förklara vad ett subjekt är."),
    )

    plan = printed_points_plan(chunks, (("body:0002",), ("body:0003",)))

    assert plan.parts == ()
    assert plan.exam_total is None
    assert "body:0001" in plan.metadata
    assert not plan.owners


def test_a_prose_rate_sentence_without_a_part_label_prints_no_total() -> None:
    chunks = _chunks(
        ("paragraph", "För varje rätt svar får du 1 poäng, så läs frågorna noga."),
        ("paragraph", "1. Förklara vad ett substantiv är."),
        ("paragraph", "2. Förklara vad ett adjektiv är."),
    )

    plan = printed_points_plan(chunks, (("body:0002",), ("body:0003",)))

    assert plan.parts == ()
    assert plan.exam_total is None
    assert not plan.owners
    assert plan.metadata == frozenset()


def _english_1_questions() -> tuple[tuple[str, ...], ...]:
    questions = recording(_ENGLISH_1, "docx_grouping_1")["questions"]
    assert isinstance(questions, list)
    grouped: list[tuple[str, ...]] = []
    for question in questions:
        assert isinstance(question, dict)
        anchors = question["anchors"]
        assert isinstance(anchors, list)
        grouped.append(tuple(str(anchor) for anchor in anchors))
    return tuple(grouped)


def test_english_1_prose_rate_sentences_print_no_total() -> None:
    chunks = corpus_chunks(_ENGLISH_1)
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    assert [by_anchor[a].kind for a in _RATE_SENTENCES] == ["paragraph", "paragraph"]
    assert "worth 1 point" in by_anchor["body:0058"].text

    plan = printed_points_plan(chunks, _english_1_questions())

    assert not {part.opener for part in plan.parts} & set(_RATE_SENTENCES)
    assert not set(plan.owners) & set(_RATE_SENTENCES)
    assert not plan.metadata & set(_RATE_SENTENCES)
    # Removing the rate sentences changes no total: they are no exam-total candidate.
    kept = tuple(chunk for chunk in chunks if chunk.anchor not in _RATE_SENTENCES)
    assert plan.exam_total == printed_points_plan(kept, _english_1_questions()).exam_total
