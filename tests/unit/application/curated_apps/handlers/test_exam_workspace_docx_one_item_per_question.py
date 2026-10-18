"""A grouped question is admitted as one item (TASK-SKRIPT-39-04-12 C3).

A reply that spreads one question's body over several entries, or puts two questions' bodies
in one entry, gets no converted item for those questions: each becomes its source review item.
"""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    NO_ITEM_REASON,
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_one_item import (
    MERGED_QUESTIONS_REASON,
    SPLIT_QUESTION_REASON,
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

# Omprov grammatik sve2, live 2026-10-17: one question, numbered sentences under one lead-in.
_QUESTION = (
    ("paragraph", "Uppgift 1.1: Subjekt (4 p)"),
    ("paragraph", "Stryk under subjektet i varje mening."),
    ("paragraph", "1. Hunden skäller på brevbäraren."),
    ("paragraph", "2. I morgon reser min syster till Malmö."),
)
_OTHER = (("paragraph", "Uppgift 1.2: Förklara vad ett predikat är. (2 p)"),)


def _state(
    *questions: tuple[tuple[str, str], ...],
) -> DocxBuildState:
    chunks: list[DocxChunk] = []
    grouped: list[tuple[str, ...]] = []
    for question in questions:
        own: list[str] = []
        for kind, text in question:
            anchor = f"body:{len(chunks) + 1:04d}"
            chunks.append(DocxChunk(anchor, kind, text, text))
            own.append(anchor)
        grouped.append(tuple(own))
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=tuple(chunks),
        questions=tuple(grouped),
    )


def _item(anchors: list[str], text: str, label: str) -> dict[str, JsonValue]:
    return {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "key_source": None,
        "facit_text": None,
        "printed_label": label,
        "body": [{"segments": [{"kind": "text", "text": text, "accepted_values": []}]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
    }


def _texts(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def _is_source_review(item: NativeExamItem, reason: str) -> bool:
    return (
        item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
        and item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        and item.review.reasons[0] == reason
    )


def test_a_question_split_into_one_item_per_sentence_becomes_one_source_review_item():
    state = _state(_QUESTION)

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003"],
                    "Hunden skäller på brevbäraren.",
                    "1",
                ),
                _item(["body:0004"], "I morgon reser min syster till Malmö.", "2"),
            ]
        },
        state,
    )

    ((item, anchors),) = state.accepted
    assert _is_source_review(item, SPLIT_QUESTION_REASON)
    assert anchors == ("body:0001", "body:0002", "body:0003", "body:0004")
    assert _texts(item) == [text for _, text in _QUESTION]
    # The question keeps the total it prints; no share of it goes to a sentence.
    assert item.points == 4
    assert state.result().document.items[0].points == 4
    assert [(e.code, e.anchors) for e in state.events if e.stage == "admission"] == [
        ("question_split", anchors)
    ]
    assert state.pending == ()


def test_a_split_question_leaves_its_neighbour_converted():
    state = _state(_QUESTION, _OTHER)

    admit_batch(
        {
            "items": [
                _item(["body:0001", "body:0002", "body:0003"], "Hunden skäller.", "1"),
                _item(["body:0004"], "I morgon reser min syster till Malmö.", "2"),
                _item(["body:0005"], "Förklara vad ett predikat är.", "Uppgift 1.2"),
            ]
        },
        state,
    )

    (split, split_anchors), (other, other_anchors) = state.accepted
    assert _is_source_review(split, SPLIT_QUESTION_REASON)
    assert split_anchors == ("body:0001", "body:0002", "body:0003", "body:0004")
    assert other.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert other_anchors == ("body:0005",)
    assert state.pending == ()


def test_two_questions_merged_into_one_item_each_become_their_own_source_review_item():
    state = _state(_QUESTION, _OTHER)

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003", "body:0004", "body:0005"],
                    "Stryk under subjektet. Förklara vad ett predikat är.",
                    "1",
                )
            ]
        },
        state,
    )

    (first, first_anchors), (second, second_anchors) = state.accepted
    assert _is_source_review(first, MERGED_QUESTIONS_REASON)
    assert _is_source_review(second, MERGED_QUESTIONS_REASON)
    assert first_anchors == ("body:0001", "body:0002", "body:0003", "body:0004")
    assert second_anchors == ("body:0005",)
    assert _texts(second) == [_OTHER[0][1]]
    assert state.pending == ()


@pytest.mark.parametrize(
    "label",
    [("heading", "Uppgift 1.1: Subjekt (4 p)"), ("paragraph", "4 p")],
    ids=["question_heading", "points_line"],
)
def test_a_separately_emitted_heading_or_points_line_is_no_split(label: tuple[str, str]):
    # The heading or points line joins the entry that holds its question's body.
    body = (("paragraph", "Stryk under subjektet i varje mening."),)
    question = (label, *body) if label[0] == "heading" else (*body, label)
    state = _state(question)
    label_anchor, body_anchor = (
        ("body:0001", "body:0002") if label[0] == "heading" else ("body:0002", "body:0001")
    )

    admit_batch(
        {
            "items": [
                _item([label_anchor], label[1], "1"),
                _item([body_anchor], "Stryk under subjektet i varje mening.", "1"),
            ]
        },
        state,
    )

    ((item, anchors),) = state.accepted
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert set(anchors) == {"body:0001", "body:0002"}
    assert not [e for e in state.events if e.code in {"question_split", "questions_merged"}]


def test_a_question_the_reply_omits_becomes_one_source_review_item():
    # Without an entry, each of the question's four chunks would be its own review item and
    # its printed 4 p would be shared out among them.
    state = _state(_OTHER, _QUESTION)

    admit_batch(
        {"items": [_item(["body:0001"], "Förklara vad ett predikat är.", "Uppgift 1.2")]}, state
    )
    document = state.result().document

    converted, omitted = document.items
    assert converted.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert _is_source_review(omitted, NO_ITEM_REASON)
    assert _texts(omitted) == [text for _, text in _QUESTION]
    assert omitted.points == 4
    assert omitted.source_anchor == "body:0002"


_NOUN = (("paragraph", "Förklara vad som kännetecknar ett substantiv. (4 p)"),)
_VERB_BODY = ("paragraph", "Förklara vad som kännetecknar ett verb.")


def _paragraph_texts(paragraphs: tuple[NativeParagraph, ...]) -> list[str]:
    return [
        segment.text
        for paragraph in paragraphs
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


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

    (first, first_anchors), (second, second_anchors) = state.accepted
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
    # and the heading still opens q2's item, where the reply lists it.
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
    assert _texts(verb)[0].startswith("Del 2: Verb")
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
    # it: it opens q2's item, as when the reply lists it as an instruction.
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
    assert _texts(verb)[0].startswith("Del 2: Verb")
    assert noun.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert verb.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert (noun.points, verb.points) == (4, 2)
    assert not [
        e
        for e in state.events
        if e.code in {"question_split", "questions_merged", "anchor_conflict"}
    ]


def test_a_one_question_part_total_reaches_the_item_that_opens_with_its_part_heading():
    # Chapter_4 shape: q2's item starts at its part heading, which no question holds, and the
    # reply's points disagree with the part's printed total. The printed total wins.
    state = _normalised_state(
        (_NOUN[0], ("heading", "Del 2: Verb (2 p)"), _VERB_BODY), ((0,), (2,))
    )
    verb = {**_item(["body:0002", "body:0003"], "Förklara vad som kännetecknar ett verb.", "2")}
    verb["points"] = 5
    noun = _item(["body:0001"], "Förklara vad som kännetecknar ett substantiv.", "1")

    admit_batch({"items": [noun, verb]}, state)
    _, opened = sorted(state.result().document.items, key=lambda item: item.sequence)

    assert opened.source_anchor == "body:0002"
    assert _texts(opened)[0].startswith("Del 2: Verb")
    assert opened.points == 2


_VERB = (
    ("paragraph", "Uppgift 2: Förklara vad som kännetecknar ett verb. (2 p)"),
    ("paragraph", "Ge två exempel på verb."),
)


@pytest.mark.parametrize("role", ["instruction", "title"])
@pytest.mark.parametrize("alone", [False, True], ids=["after_q1", "alone"])
def test_a_question_the_reply_lists_as_metadata_becomes_one_source_review_item(
    role: str, alone: bool
):
    # Review-1 F4: no item holds q2 although no chunk of it stays unclaimed.
    state = _state(_VERB) if alone else _state(_OTHER, _VERB)
    own: list[JsonValue] = [
        chunk.anchor for chunk in state.chunks if chunk.text in {t for _, t in _VERB}
    ]
    metadata: dict[str, JsonValue] = {"text": " ".join(t for _, t in _VERB), "source_anchors": own}
    content: dict[str, JsonValue] = {
        "items": [] if alone else [_item(["body:0001"], "Förklara vad ett predikat är.", "1.2")]
    }
    if role == "title":
        content["title"] = metadata
    else:
        content["instructions"] = [metadata]

    admit_batch(content, state)
    result = state.result()
    document = NativeExamDocument.model_validate(result.document.model_dump())

    assert len(document.items) == (1 if alone else 2)
    omitted = document.items[-1]
    assert _is_source_review(omitted, NO_ITEM_REASON)
    assert _texts(omitted) == [text for _, text in _VERB]
    assert omitted.source_anchor == own[0]
    placed = _paragraph_texts(document.instructions) + [
        text for parent in document.parents for text in _paragraph_texts(parent.instruction)
    ]
    assert not [text for text in placed for _, own_text in _VERB if own_text in text]
    assert not [own_text for _, own_text in _VERB if own_text in document.title]
