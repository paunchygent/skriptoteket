"""A part line opens a parent whatever its number of questions (user ruling 2026-10-18, DEL 4).

A part-labelled line whose part identity no other part line repeats opens a parent, like
DEL 1-3, also over one question: the line is the parent's instruction, the part's total its
printed total, and the question's item no longer opens with the line. Part-labelled lines
that repeat one identity ("Part 3, Question 1 (1 point)", "Part 3, Question 2 (1 point)")
are question headings inside that part: each opens its question's item and forms no parent.
"""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    assign_points_lines,
    manifest_questions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

pytestmark = pytest.mark.unit

_NOUN = "Förklara vad som kännetecknar ett substantiv."
_VERB = "Förklara vad som kännetecknar ett verb."


def _state(chunks: tuple[tuple[str, str], ...], grouped: tuple[tuple[int, ...], ...]):
    """The batch state built as the pipeline builds it: from the normalised manifest."""
    docx = tuple(
        DocxChunk(f"body:{index + 1:04d}", kind, text, text)
        for index, (kind, text) in enumerate(chunks)
    )
    manifest = ExamManifest(
        questions=tuple(
            ManifestQuestion(f"q{number + 1}", tuple(docx[i].anchor for i in own), (), ())
            for number, own in enumerate(grouped)
        ),
        contexts=(),
        title_anchors=(),
        header=(),
        invalid_anchors=(),
        duplicate_anchors=(),
        unplaced_anchors=(),
    )
    normalised = assign_points_lines(manifest, docx)
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=docx,
        questions=manifest_questions(normalised),
    )


def _item(anchors: list[str], text: str, points: int) -> dict[str, JsonValue]:
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": None,
        "body": [
            {"segments": [{"kind": "text", "text": line, "accepted_values": []}]}
            for line in text.split("\n")
        ],
        "points": points,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _converted(state: DocxBuildState) -> NativeExamDocument:
    document = state.result().document
    assert all(i.review.parse_origin is NativeParseOrigin.LLM_PARSED for i in document.items)
    assert not [
        e
        for e in state.events
        if e.code in {"question_split", "questions_merged", "anchor_conflict"}
    ]
    return document


@pytest.mark.parametrize("kind", ["heading", "paragraph"])
def test_a_part_line_over_one_question_opens_a_one_child_parent(kind: str):
    # Each part holds one question; the reply lists each part line in its question's entry,
    # as the live replies do for DEL 4.
    state = _state(
        (
            (kind, "Del 1: Substantiv (4 p)"),
            ("paragraph", _NOUN),
            (kind, "Del 2: Verb (2 p)"),
            ("paragraph", _VERB),
        ),
        ((0, 1), (2, 3)),
    )

    admit_batch(
        {
            "items": [
                _item(["body:0001", "body:0002"], _NOUN, 3),
                _item(["body:0003", "body:0004"], _VERB, 5),
            ]
        },
        state,
    )
    document = _converted(state)

    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert [(p.item_ids, p.printed_total) for p in document.parents] == [
        ((noun.item_id,), 4),
        ((verb.item_id,), 2),
    ]
    assert [body_text_lines(p.instruction) for p in document.parents] == [
        ("Del 1: Substantiv",),
        ("Del 2: Verb",),
    ]
    assert not [line for line in body_text_lines(noun.body) if line.startswith("Del ")]
    assert not [line for line in body_text_lines(verb.body) if line.startswith("Del ")]
    assert (noun.points, verb.points) == (4, 2)


def test_a_part_paragraph_a_summary_totals_opens_a_one_child_parent():
    # The user's DEL 4 shape: the part paragraph prints no total of its own, the summary
    # gives it one, and its one question prints different points of its own.
    state = _state(
        (
            ("paragraph", "Del 1: Substantiv (4 p) • Del 2: Verb (15 p)"),
            ("paragraph", "DEL 1: SUBSTANTIV"),
            ("paragraph", f"{_NOUN} (4 p)"),
            ("paragraph", "DEL 2: VERB"),
            ("paragraph", f"{_VERB} (12 p)"),
        ),
        ((1, 2), (3, 4)),
    )

    admit_batch(
        {
            "items": [
                _item(["body:0002", "body:0003"], _NOUN, 4),
                _item(["body:0004", "body:0005"], _VERB, 12),
            ]
        },
        state,
    )
    document = _converted(state)

    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert [(p.item_ids, p.printed_total) for p in document.parents] == [
        ((noun.item_id,), 4),
        ((verb.item_id,), 15),
    ]
    assert body_text_lines(document.parents[1].instruction) == ("DEL 2: VERB",)
    assert body_text_lines(verb.body)[0] == _VERB
    # The question keeps what it prints itself; the parent shows the printed difference.
    assert verb.points == 12


@pytest.mark.parametrize("kind", ["heading", "paragraph"])
def test_part_lines_repeating_one_identity_stay_question_headings(kind: str):
    # Chapter_4 shape: "Part 3, Question N (1 point)" over one question each. The repeated
    # identity makes each line its question's heading: no parent, the line opens its item,
    # and its total wins over the reply's points.
    state = _state(
        (
            (kind, "Part 3, Question 1 (1 point)"),
            ("paragraph", _NOUN),
            (kind, "Part 3, Question 2 (1 point)"),
            ("paragraph", _VERB),
        ),
        ((0, 1), (2, 3)),
    )

    admit_batch(
        {
            "items": [
                _item(["body:0001", "body:0002"], _NOUN, 4),
                _item(["body:0003", "body:0004"], _VERB, 4),
            ]
        },
        state,
    )
    document = _converted(state)

    first, second = sorted(document.items, key=lambda item: item.sequence)
    assert document.parents == ()
    assert body_text_lines(first.body)[0].startswith("Part 3, Question 1")
    assert body_text_lines(second.body)[0].startswith("Part 3, Question 2")
    assert (first.points, second.points) == (1, 1)
