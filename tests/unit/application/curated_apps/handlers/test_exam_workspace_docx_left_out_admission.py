"""A converted item holds the own chunks of its question that the reply leaves out (D41). Only a
chunk whose wording the item lacks, without points labels, numbering and answer or facit lines,
shows under the item's check mark as printed (D4). A reply without points takes the one points
label the item's own chunks print, and the label leaves the stem and title (D3)."""

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
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItem,
    NativeItemReviewState,
    NativeParseOrigin,
    NativeTextSegment,
)

pytestmark = pytest.mark.unit

_STEM = "1. Beskriv kort hur en intervju planeras."
_FACIT = "Svar: syfte, urval och frågor bestäms i förväg."


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _state(*texts: str) -> DocxBuildState:
    chunks = tuple(_chunk(f"body:{n:04d}", text) for n, text in enumerate(texts, start=1))
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(tuple(c.anchor for c in chunks),),
    )


def _text(text: str) -> dict[str, JsonValue]:
    return {"kind": "text", "text": text, "accepted_values": []}


def _item(anchors: list[str], **fields: JsonValue) -> dict[str, JsonValue]:
    item: dict[str, JsonValue] = {
        "source_anchors": list(anchors),
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "title": None,
        "printed_label": "1",
        "body": [{"segments": [_text(_STEM[3:])]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "marking_guide": "",
    }
    item.update(fields)
    return item


def _stem_texts(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def test_an_own_facit_line_listed_only_as_an_answer_key_joins_the_item_unmarked():
    state = _state(_STEM, _FACIT)

    admit_batch(
        {"answer_key_anchors": ["body:0002"], "items": [_item(["body:0001"], title=_STEM)]}, state
    )

    assert state.key_anchors == set()
    ((admitted, anchors),) = state.accepted
    assert anchors == ("body:0001", "body:0002")
    assert admitted.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()
    assert state.events == []
    assert state.pending == ()


@pytest.mark.parametrize(
    "facit",
    [
        "Correct answer: syfte, urval och frågor",
        "Rätt svar: syfte, urval och frågor",
        "(Answer key: syfte, urval och frågor)",
        "Svarsexempel: syfte, urval och frågor",
        "Facit: syfte, urval och frågor",
        "1. Correct answer: syfte, urval och frågor",
        "b) Svar: syfte, urval och frågor",
    ],
)
def test_an_own_facit_line_the_reply_leaves_out_is_not_flagged_in_any_printed_form(facit):
    state = _state(_STEM, facit)

    admit_batch({"items": [_item(["body:0001"])]}, state)

    ((admitted, anchors),) = state.accepted
    assert anchors == ("body:0001", "body:0002")
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()


def test_an_answer_options_line_the_reply_leaves_out_is_still_flagged():
    options = "Svarsalternativ: intervju, enkät eller observation"
    state = _state(_STEM, options)

    admit_batch({"items": [_item(["body:0001"])]}, state)

    ((admitted, _),) = state.accepted
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, options)


def test_a_reply_that_leaves_out_the_stem_anchor_but_copies_its_wording_is_not_flagged():
    lead = "Läs dikten nedan och svara på frågan."
    state = _state(lead, _STEM)

    body = [{"segments": [_text(lead)]}, {"segments": [_text(_STEM[3:])]}]
    admit_batch({"items": [_item(["body:0002"], body=body)]}, state)

    ((admitted, anchors),) = state.accepted
    assert anchors == ("body:0002", "body:0001")
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()


def test_a_reply_that_drops_a_stem_sentence_is_flagged_with_that_paragraph():
    lead = "Läs dikten nedan. Tänk särskilt på diktens rytm och rim."
    state = _state(lead, _STEM)

    body = [{"segments": [_text("Läs dikten nedan.")]}, {"segments": [_text(_STEM[3:])]}]
    admit_batch({"items": [_item(["body:0002"], body=body)]}, state)

    ((admitted, _),) = state.accepted
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, lead)
    assert [(e.code, e.anchors) for e in state.events] == [("own_chunks_left_out", ("body:0001",))]


@pytest.mark.parametrize(
    ("dropped", "kept"),
    [
        ("x + y = 7", "Beräkna summan."),
        ("Förklara hur ånga blir vatten.", "Förklara hur vatten blir ånga."),
        ("Skriv i meter.", "Skriv meter."),
    ],
    ids=["formula", "reversed-sentence", "one-letter-word"],
)
def test_a_dropped_paragraph_is_flagged_even_when_the_item_shares_its_words(dropped, kept):
    state = _state(dropped, kept)

    admit_batch(
        {"items": [_item(["body:0002"], body=[{"segments": [_text(kept)]}])]},
        state,
    )

    ((admitted, _),) = state.accepted
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, dropped)


def test_a_dropped_stem_read_through_its_gap_answer_is_not_flagged():
    stem = "1. The bands ____ (spelar) at the festival."
    state = _state("Fyll i rätt form.", stem)
    body = [
        {"segments": [_text("Fyll i rätt form.")]},
        {
            "segments": [
                _text("The bands "),
                {"kind": "gap", "text": None, "accepted_values": ["play"]},
                _text(" (spelar) at the festival."),
            ]
        },
    ]

    admit_batch({"items": [_item(["body:0001"], kind="gap_fill", body=body)]}, state)

    ((admitted, anchors),) = state.accepted
    assert anchors == ("body:0001", "body:0002")
    assert admitted.review.reasons == ()


def test_a_dropped_line_of_inline_options_is_read_option_by_option():
    options = "A) play B) plays"
    state = _state(_STEM, options)
    choices: list[JsonValue] = [
        {"text": "play", "correct": True},
        {"text": "plays", "correct": False},
    ]

    admit_batch(
        {
            "items": [
                _item(["body:0001"], kind="single_choice", choices=choices, marking_guide=None)
            ]
        },
        state,
    )

    ((admitted, _),) = state.accepted
    assert admitted.review.reasons == ()


@pytest.mark.parametrize(
    ("stem", "flagged"),
    [("absence without permission", True), ("absence without permission: truancy", False)],
    ids=["one-cell-missing", "every-cell-read"],
)
def test_a_dropped_table_is_read_cell_by_cell(stem, flagged):
    table = "1. absence without permission | ____ | A. truancy"
    state = _state(stem, table)

    admit_batch({"items": [_item(["body:0001"], body=[{"segments": [_text(stem)]}])]}, state)

    ((admitted, _),) = state.accepted
    assert admitted.review.reasons == ((LEFT_OUT_REASON, table) if flagged else ())


def test_a_points_label_split_across_text_segments_leaves_the_stem():
    stem = "Vilket ord är ett substantiv? (1 p)"
    state = _state(stem)
    body = [{"segments": [_text("Vilket ord är ett substantiv? (1"), _text(" p)")]}]

    admit_batch({"items": [_item(["body:0001"], body=body, points=None)]}, state)

    ((admitted, _),) = state.accepted
    assert admitted.points == 1
    assert _stem_texts(admitted) == ["Vilket ord är ett substantiv?"]


def test_a_choice_stem_ending_in_one_point_label_takes_the_point_and_loses_the_label():
    stem = "Vilket ord är ett substantiv? (1 p)"
    state = _state(stem, "A. springa", "B. bord", "C. snabb")
    choices: list[JsonValue] = [
        {"text": "springa", "correct": False},
        {"text": "bord", "correct": True},
        {"text": "snabb", "correct": False},
    ]

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003", "body:0004"],
                    kind="single_choice",
                    title=stem,
                    body=[{"segments": [_text(stem)]}],
                    points=None,
                    choices=choices,
                    marking_guide=None,
                )
            ]
        },
        state,
    )

    ((admitted, _),) = state.accepted
    assert admitted.points == 1
    assert admitted.title == "Vilket ord är ett substantiv?"
    assert _stem_texts(admitted) == ["Vilket ord är ett substantiv?"]
    assert admitted.review.reasons == ()


@pytest.mark.parametrize(
    "texts",
    [
        ("Vilket ord är ett substantiv?", "A. bord", "B. springa"),
        ("Vilket ord är ett substantiv? (1 p)", "A. bord (1 p)", "B. springa"),
        ("Vilket ord är ett substantiv? (0 p)", "A. bord", "B. springa"),
    ],
    ids=["no-label", "two-labels", "zero-points"],
)
def test_a_reply_without_points_keeps_no_points_without_exactly_one_positive_label(texts):
    state = _state(*texts)
    choices: list[JsonValue] = [
        {"text": "bord", "correct": True},
        {"text": "springa", "correct": False},
    ]

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003"],
                    kind="single_choice",
                    body=[{"segments": [_text(texts[0])]}],
                    points=None,
                    choices=choices,
                    marking_guide=None,
                )
            ]
        },
        state,
    )

    ((admitted, _),) = state.accepted
    assert admitted.points is None
    assert _stem_texts(admitted) == [texts[0]]


def test_points_the_reply_gives_win_over_a_printed_label():
    stem = "Vilket ord är ett substantiv? (1 p)"
    state = _state(stem)

    admit_batch({"items": [_item(["body:0001"], body=[{"segments": [_text(stem)]}])]}, state)

    ((admitted, _),) = state.accepted
    assert admitted.points == 2
    assert _stem_texts(admitted) == [stem]


def test_a_points_paragraph_the_reply_does_not_list_still_gives_its_question_the_points():
    state = _state("Vilket ord är ett substantiv?", "A. bord", "B. springa", "(1 p)")
    choices: list[JsonValue] = [
        {"text": "bord", "correct": True},
        {"text": "springa", "correct": False},
    ]

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001", "body:0002", "body:0003"],
                    kind="single_choice",
                    body=[{"segments": [_text("Vilket ord är ett substantiv?")]}],
                    points=None,
                    choices=choices,
                    marking_guide=None,
                )
            ]
        },
        state,
    )

    ((admitted, anchors),) = state.accepted
    assert admitted.points == 1
    assert anchors[-1] == "body:0004"
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()
