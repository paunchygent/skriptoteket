"""Adversarial table for the one owner of a printed points line (TASK-SKRIPT-39-04-11 D2)."""

from dataclasses import dataclass, replace

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    HeaderAnchor,
    ManifestQuestion,
    SharedContext,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    assign_points_lines,
    line_points,
)

pytestmark = pytest.mark.unit

_Chunk = tuple[str, str]  # (kind, text)


def _chunk(index: int, kind: str, text: str) -> DocxChunk:
    return DocxChunk(anchor=f"a{index}", kind=kind, text=text, marked_text=text)


@dataclass(frozen=True)
class _Case:
    name: str
    chunks: tuple[_Chunk, ...]
    questions: dict[str, tuple[int, ...]]  # question id -> chunk indexes
    line: int  # index of the points line under test
    placement: str  # unplaced | context_q1 | context_exam | header | key
    owner: str | None  # question id that must own the line, or None


_P = "paragraph"
_H = "heading"
_LINE = (_P, "Poäng: 2 poäng")

_CASES = (
    _Case(
        "1 unplaced after q1",
        ((_P, "Q1"), _LINE, (_P, "Q2")),
        {"q1": (0,), "q2": (2,)},
        1,
        "unplaced",
        "q1",
    ),
    _Case(
        "2a context owner q1",
        ((_P, "Q1"), _LINE, (_P, "Q2")),
        {"q1": (0,), "q2": (2,)},
        1,
        "context_q1",
        "q1",
    ),
    _Case(
        "2b context owner exam",
        ((_P, "Q1"), _LINE, (_P, "Q2")),
        {"q1": (0,), "q2": (2,)},
        1,
        "context_exam",
        "q1",
    ),
    _Case(
        "3 header question_total",
        ((_P, "Q1"), _LINE, (_P, "Q2")),
        {"q1": (0,), "q2": (2,)},
        1,
        "header",
        "q1",
    ),
    _Case(
        "4 key anchor", ((_P, "Q1"), _LINE, (_P, "Q2")), {"q1": (0,), "q2": (2,)}, 1, "key", "q1"
    ),
    _Case(
        "5 section closing line stays",
        (
            (_H, "Del 1: 15 poäng"),
            (_P, "Q1"),
            (_P, "Q2"),
            (_P, "Poäng: 15 poäng"),
            (_H, "Del 2: 3 poäng"),
        ),
        {"q1": (1,), "q2": (2,)},
        3,
        "unplaced",
        None,
    ),
    # A line that restates its part's total closes the part, even after its only question.
    _Case(
        "6 one-question section",
        ((_H, "Del 1: 4 poäng"), (_P, "Q1"), (_P, "Poäng: 4 poäng")),
        {"q1": (1,)},
        2,
        "unplaced",
        None,
    ),
    _Case(
        "7 value differs from heading",
        ((_H, "Del 1: 15 poäng"), (_P, "Q1"), (_P, "Q2"), _LINE),
        {"q1": (1,), "q2": (2,)},
        3,
        "unplaced",
        "q2",
    ),
    _Case(
        "8 before first question",
        ((_P, "Total: 36 poäng"), (_P, "Q1")),
        {"q1": (1,)},
        0,
        "unplaced",
        None,
    ),
    # A question's points label before its question heads the question right after it.
    _Case(
        "9 heading between question and line",
        ((_P, "Q1"), (_H, "Del 2: 5 poäng"), (_P, "Poäng: 5 poäng"), (_P, "Q2")),
        {"q1": (0,), "q2": (3,)},
        2,
        "unplaced",
        "q2",
    ),
    _Case(
        "10 heading prints points", ((_P, "Q1"), (_H, "(2 p)")), {"q1": (0,)}, 1, "unplaced", None
    ),
    _Case(
        "12 question label before a part line heads the next question",
        (_LINE, (_H, "Del 1: 10 poäng"), (_P, "Q1"), (_P, "Q2")),
        {"q1": (2,), "q2": (3,)},
        0,
        "unplaced",
        "q1",
    ),
    _Case(
        "11 line with more words",
        ((_P, "Q1"), (_P, "Svara med 2 hela meningar för 2 poäng"), (_P, "Q2")),
        {"q1": (0,), "q2": (2,)},
        1,
        "unplaced",
        None,
    ),
)


def _build(case: _Case) -> tuple[tuple[DocxChunk, ...], ExamManifest]:
    chunks = tuple(_chunk(i, kind, text) for i, (kind, text) in enumerate(case.chunks))
    own = {i for indexes in case.questions.values() for i in indexes}
    line = chunks[case.line].anchor
    key = (line,) if case.placement == "key" else ()
    questions = tuple(
        ManifestQuestion(
            question_id=qid,
            anchors=tuple(chunks[i].anchor for i in indexes),
            subpart_anchors=(),
            key_anchors=key if qid == "q1" else (),
        )
        for qid, indexes in case.questions.items()
    )
    contexts = (
        (SharedContext(anchor=line, scope="other", owner=case.placement[8:], governs=()),)
        if case.placement.startswith("context_")
        else ()
    )
    header = (
        (HeaderAnchor(anchor=line, kind="question_total", governs=("q1",)),)
        if case.placement == "header"
        else ()
    )
    placed_elsewhere = case.placement != "unplaced"
    unplaced = tuple(
        c.anchor
        for i, c in enumerate(chunks)
        if i not in own and not (placed_elsewhere and c.anchor == line)
    )
    manifest = ExamManifest(
        questions=questions,
        contexts=contexts,
        title_anchors=(),
        header=header,
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=unplaced,
    )
    return chunks, manifest


@pytest.mark.parametrize("case", _CASES, ids=lambda case: case.name)
def test_points_line_owner(case: _Case) -> None:
    chunks, manifest = _build(case)
    line = chunks[case.line].anchor
    order = {c.anchor: i for i, c in enumerate(chunks)}

    result = assign_points_lines(manifest, chunks)

    if case.owner is None:
        assert all(line not in (*q.anchors, *q.key_anchors) for q in result.questions)
        if line_points(chunks[case.line]) is not None:
            # A points line no question owns is unplaced metadata wherever it was tagged.
            assert line in result.unplaced_anchors
            assert all(c.anchor != line for c in result.contexts)
            assert all(h.anchor != line for h in result.header)
        return
    for question in result.questions:
        if question.question_id == case.owner:
            assert line in question.anchors
            assert list(question.anchors) == sorted(question.anchors, key=order.__getitem__)
        else:
            assert line not in question.anchors
        assert line not in question.key_anchors
    assert line not in result.unplaced_anchors
    assert all(c.anchor != line for c in result.contexts)
    assert all(h.anchor != line for h in result.header)
    untouched = replace(
        result,
        questions=manifest.questions,
        contexts=manifest.contexts,
        header=manifest.header,
        unplaced_anchors=manifest.unplaced_anchors,
    )
    assert untouched == manifest


def test_manifest_without_points_line_is_returned_identically() -> None:
    case = _Case(
        "12",
        ((_P, "Q1"), (_P, "Svara kort."), (_P, "Q2")),
        {"q1": (0,), "q2": (2,)},
        1,
        "unplaced",
        None,
    )
    chunks, manifest = _build(case)
    assert assign_points_lines(manifest, chunks) == manifest


@pytest.mark.parametrize(
    ("kind", "text", "expected"),
    [
        (_P, "Poäng: 2 poäng", 2),
        (_P, "(1,5 p)", 1.5),
        (_H, "Poäng: 2 poäng", None),
        (_P, "Poäng: 2 poäng, 3 poäng", None),
    ],
)
def test_line_points(kind: str, text: str, expected: int | float | None) -> None:
    assert line_points(_chunk(0, kind, text)) == expected


def test_a_section_line_tagged_as_a_header_loses_the_tag_and_no_question_owns_it() -> None:
    (closing,) = [case for case in _CASES if case.name.startswith("5 ")]
    chunks, manifest = _build(replace(closing, placement="header"))
    line = chunks[closing.line].anchor

    result = assign_points_lines(manifest, chunks)

    assert result.header == ()
    assert line in result.unplaced_anchors
    assert result.questions == manifest.questions


@pytest.mark.parametrize("placement", ["anchors", "key_anchors"])
def test_a_section_line_a_question_holds_is_released(placement: str) -> None:
    (closing,) = [case for case in _CASES if case.name.startswith("5 ")]
    chunks, manifest = _build(closing)
    line = chunks[closing.line].anchor
    q2 = manifest.questions[1]
    if placement == "anchors":
        held = replace(q2, anchors=(*q2.anchors, line))
    else:
        held = replace(q2, key_anchors=(*q2.key_anchors, line))
    manifest = replace(
        manifest,
        questions=(manifest.questions[0], held),
        unplaced_anchors=tuple(a for a in manifest.unplaced_anchors if a != line),
    )

    result = assign_points_lines(manifest, chunks)

    assert all(line not in (*q.anchors, *q.key_anchors) for q in result.questions)
    assert line in result.unplaced_anchors
