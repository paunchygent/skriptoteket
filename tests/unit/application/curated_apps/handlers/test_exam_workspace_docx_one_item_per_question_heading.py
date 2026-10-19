"""A heading or part label stays with the question it opens (TASK-SKRIPT-39-04-12 C3).

An entry holding another question's heading merges both questions; a heading the grouping
misplaces still belongs to the question it opens; a part-labelled heading opens its own
one-child parent and never enters an item body.
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
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_one_item import (
    MERGED_QUESTIONS_REASON,
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_one_item_test_support import (
    _is_source_review,
    _item,
    _paragraph_texts,
    _state,
    _texts,
)

pytestmark = pytest.mark.unit

_NOUN = (("paragraph", "Förklara vad som kännetecknar ett substantiv. (4 p)"),)
_VERB_BODY = ("paragraph", "Förklara vad som kännetecknar ett verb.")


@pytest.mark.parametrize("heading_kind", ["heading", "paragraph"])
def test_an_entry_holding_another_questions_heading_merges_both_questions(heading_kind: str):
    # Review-1 F1: q2's own heading in q1's entry makes that entry hold two questions, also
    # when the heading is a label line that would join its own question's body.
    verb = ((heading_kind, "Uppgift 2: Verb (2 p)"), _VERB_BODY)
    state = _state(_NOUN, verb)

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002"],
                    "Förklara vad som kännetecknar ett substantiv. Uppgift 2: Verb",
                    "1",
                ),
                _item(["body:0003"], "Förklara vad som kännetecknar ett verb.", "2"),
            ]
        },
        state,
    )
    document = state.result().document

    (first, first_anchors), (second, second_anchors) = [(a.item, h) for a, h in state.accepted]
    assert _is_source_review(first, MERGED_QUESTIONS_REASON)
    assert _is_source_review(second, MERGED_QUESTIONS_REASON)
    assert first_anchors == ("body:0001",)
    assert set(second_anchors) == {"body:0002", "body:0003"}
    assert _texts(first) == [_NOUN[0][1]]
    assert _texts(second) == [text for _, text in verb]
    assert [e.code for e in state.events if e.stage == "admission"] == [
        "questions_merged",
        "questions_merged",
    ]
    assert len(document.items) == 2
    assert not [
        item
        for item in document.items
        if item.source_anchor == "body:0001" and _texts(item)[0].startswith("Uppgift 2")
    ]


def _normalised_state(
    chunks: tuple[tuple[str, str], ...], grouped: tuple[tuple[int, ...], ...]
) -> DocxBuildState:
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


@pytest.mark.parametrize("reverse", [False, True], ids=["q1_first", "q2_first"])
def test_a_total_heading_the_grouping_misplaces_belongs_to_the_question_it_opens(reverse: bool):
    # Review-2 F1: the grouping gives q2's heading to q1. The heading opens a part over q2
    # alone, so the normalised manifest gives it to q2, and every consumer reads that owner:
    # whatever the reply order, q2's item opens with the heading and q1's never holds it.
    heading = ("heading", "Uppgift 2: Verb (2 p)")
    state = _normalised_state((_NOUN[0], heading, _VERB_BODY), ((0, 1), (2,)))
    entries: list[JsonValue] = [
        _item(["body:0001"], "Förklara vad som kännetecknar ett substantiv.", "1"),
        _item(["body:0002", "body:0003"], "Förklara vad som kännetecknar ett verb.", "2"),
    ]

    admit_batch({"items": entries[::-1] if reverse else entries}, state)
    document = state.result().document

    noun, verb = sorted(document.items, key=lambda item: item.source_anchor or "")
    assert noun.source_anchor == "body:0001"
    assert not [text for text in _texts(noun) if "Uppgift 2" in text]
    assert verb.source_anchor == "body:0002"
    assert _texts(verb)[0].startswith("Uppgift 2: Verb")
    assert noun.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert verb.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert (noun.points, verb.points) == (4, 2)
    assert not [
        e
        for e in state.events
        if e.code in {"question_split", "questions_merged", "anchor_conflict"}
    ]


@pytest.mark.parametrize("reverse", [False, True], ids=["q1_first", "q2_first"])
def test_a_part_labelled_one_question_heading_misplaced_by_the_grouping_ignores_reply_order(
    reverse: bool,
):
    # Control for review-2 F1: the grouping gives q2's part-labelled heading to q1. A
    # part-labelled line is never a question anchor, so the normalised manifest gives it to
    # no question. Whatever the reply order, both questions stay as the model parsed them,
    # and the heading opens q2's one-child parent (user ruling 2026-10-18).
    heading = ("heading", "Del 2: Verb (2 p)")
    state = _normalised_state((_NOUN[0], heading, _VERB_BODY), ((0, 1), (2,)))
    entries: list[JsonValue] = [
        _item(["body:0001"], "Förklara vad som kännetecknar ett substantiv.", "1"),
        _item(["body:0002", "body:0003"], "Förklara vad som kännetecknar ett verb.", "2"),
    ]

    assert "body:0002" not in state.question_by_anchor
    assert [own for own in state.questions] == [("body:0001",), ("body:0003",)]

    admit_batch({"items": entries[::-1] if reverse else entries}, state)
    document = state.result().document

    noun, verb = sorted(document.items, key=lambda item: item.source_anchor or "")
    assert noun.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert verb.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert not [text for text in _texts(noun) if "Del 2" in text]
    assert not [text for text in _texts(verb) if "Del 2" in text]
    assert _texts(noun)[0] == "Förklara vad som kännetecknar ett substantiv."
    assert _texts(verb)[0] == "Förklara vad som kännetecknar ett verb."
    assert [(p.item_ids, _paragraph_texts(p.instruction)) for p in document.parents] == [
        ((verb.item_id,), ["Del 2: Verb"])
    ]
    assert not [
        e
        for e in state.events
        if e.code in {"question_split", "questions_merged", "anchor_conflict"}
    ]


@pytest.mark.parametrize("reverse", [False, True], ids=["q1_first", "q2_first"])
def test_a_part_heading_the_reply_lists_with_another_question_opens_its_own_question(
    reverse: bool,
):
    # Review-2 F1: the reply copies the grouping's misplacement and lists q2's part-labelled
    # heading in q1's entry. The heading opens a part over q2 alone, so q1's item never holds
    # it: it opens q2's one-child parent (user ruling 2026-10-18).
    heading = ("heading", "Del 2: Verb (2 p)")
    state = _normalised_state((_NOUN[0], heading, _VERB_BODY), ((0, 1), (2,)))
    entries: list[JsonValue] = [
        _item(["body:0001", "body:0002"], "Förklara vad som kännetecknar ett substantiv.", "1"),
        _item(["body:0003"], "Förklara vad som kännetecknar ett verb.", "2"),
    ]

    admit_batch({"items": entries[::-1] if reverse else entries}, state)
    document = state.result().document

    noun, verb = sorted(document.items, key=lambda item: item.sequence)
    assert noun.source_anchor == "body:0001"
    assert not [text for text in _texts(noun) if "Del 2" in text]
    assert not [text for text in _texts(verb) if "Del 2" in text]
    assert _texts(noun)[0] == "Förklara vad som kännetecknar ett substantiv."
    assert _texts(verb)[0] == "Förklara vad som kännetecknar ett verb."
    assert [(p.item_ids, p.printed_total) for p in document.parents] == [((verb.item_id,), 2)]
    assert noun.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert verb.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert (noun.points, verb.points) == (4, 2)
    assert not [
        e
        for e in state.events
        if e.code in {"question_split", "questions_merged", "anchor_conflict"}
    ]


def test_a_one_question_part_total_reaches_its_item_and_its_one_child_parent():
    # Q2's part heading names its own part, so it opens q2's one-child parent (user ruling
    # 2026-10-18) and q2's item starts at its own chunk. The reply's points disagree with the
    # part's printed total; the printed total wins and checks the parent.
    state = _normalised_state(
        (_NOUN[0], ("heading", "Del 2: Verb (2 p)"), _VERB_BODY), ((0,), (2,))
    )
    verb = {**_item(["body:0002", "body:0003"], "Förklara vad som kännetecknar ett verb.", "2")}
    verb["points"] = 5
    noun = _item(["body:0001"], "Förklara vad som kännetecknar ett substantiv.", "1")

    admit_batch({"items": [noun, verb]}, state)
    _, opened = sorted(state.result().document.items, key=lambda item: item.sequence)

    assert opened.source_anchor == "body:0003"
    assert not [text for text in _texts(opened) if "Del 2" in text]
    assert _texts(opened)[0] == "Förklara vad som kännetecknar ett verb."
    assert opened.points == 2
    assert [(p.item_ids, p.printed_total) for p in state.result().document.parents] == [
        ((opened.item_id,), 2)
    ]
