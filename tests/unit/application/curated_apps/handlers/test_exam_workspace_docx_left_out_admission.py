"""A converted item holds the own chunks of its question that the reply leaves out (D41). Only a
chunk no body paragraph, choice or matching entry is aligned to shows under the item's check
mark as printed; a source answer or facit line is never marked (D4, TASK-SKRIPT-39-04-14). A
reply without points takes the one points label the item's own chunks print, and the label
leaves the stem (D3)."""

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_left_out_test_support import (
    _STEM,
    _item,
    _state,
    _text,
)

pytestmark = pytest.mark.unit

_FACIT = "Svar: syfte, urval och frågor bestäms i förväg."


def _stem_texts(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def test_an_own_facit_line_listed_only_as_an_answer_key_joins_the_item_unmarked():
    state = _state(_STEM, _FACIT)

    admit_batch({"answer_key_anchors": ["body:0002"], "items": [_item(["body:0001"])]}, state)

    assert state.key_anchors == set()
    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert anchors == ("body:0001", "body:0002")
    assert admitted.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()
    assert [(e.code, e.item, e.anchors) for e in state.events if e.stage == "formatting"] == [
        ("exact", 0, ("body:0001",))
    ]
    assert [e for e in state.events if e.stage != "formatting"] == []
    assert state.pending == ()


def test_an_own_facit_line_the_grouping_and_the_reply_list_as_a_key_is_its_answer_key():
    # Live SA24 and Diagnostic 85 2026-10-16: the grouping listed each facit line both among
    # its question's own chunks and as its key; the reply's facit_text rewords the line.
    state = _state(
        "11. ______ (s…t) – A drug that keeps you awake.",
        _FACIT,
        grouped_keys=frozenset({"body:0002"}),
    )
    gap: JsonValue = {"kind": "gap", "text": None, "accepted_values": ["stimulant"]}
    body: JsonValue = [{"segments": [gap, _text(" (s…t) – A drug that keeps you awake.")]}]

    admit_batch(
        {
            "answer_key_anchors": ["body:0002"],
            "items": [
                _item(
                    ["body:0001"],
                    kind="gap_fill",
                    key_source="copied",
                    facit_text="syfte, urval och frågor",
                    body=body,
                    printed_label="11",
                )
            ],
        },
        state,
    )

    assert state.key_anchors == {"body:0002"}
    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert anchors == ("body:0001",)
    assert _FACIT not in " ".join(_stem_texts(admitted))
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE


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

    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert anchors == ("body:0001", "body:0002")
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()


def test_an_answer_options_line_the_reply_leaves_out_is_still_flagged():
    options = "Svarsalternativ: intervju, enkät eller observation"
    state = _state(_STEM, options)

    admit_batch({"items": [_item(["body:0001"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, options)


def test_a_reply_that_leaves_out_the_stem_anchor_but_copies_its_wording_is_not_flagged():
    lead = "Läs dikten nedan och svara på frågan."
    state = _state(lead, _STEM)

    body: JsonValue = [{"segments": [_text(lead)]}, {"segments": [_text(_STEM[3:])]}]
    admit_batch({"items": [_item(["body:0002"], body=body)]}, state)

    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert anchors == ("body:0002", "body:0001")
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()


def test_a_reply_that_shortens_an_aligned_stem_paragraph_shows_its_chunk():
    # The reply drops the lead's second sentence, but its first sentence is aligned to the lead
    # chunk: the item shows that chunk, so it is no left-out chunk (TASK-SKRIPT-39-04-14 D4).
    lead = "Läs dikten nedan. Tänk särskilt på diktens rytm och rim."
    state = _state(lead, _STEM)

    body: JsonValue = [{"segments": [_text("Läs dikten nedan.")]}, {"segments": [_text(_STEM[3:])]}]
    admit_batch({"items": [_item(["body:0002"], body=body)]}, state)

    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert anchors == ("body:0002", "body:0001")
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert [e for e in state.events if e.stage != "formatting"] == []


@pytest.mark.parametrize(
    ("dropped", "kept"),
    [
        ("x + y = 7", "Beräkna summan."),
        ("Förklara hur ånga blir vatten.", "Förklara hur vatten blir ånga."),
        ("Skriv i meter.", "Skriv meter."),
        ("Beräkna x - y = 7.", "Beräkna x y = 7."),
        ("Beräkna x − y = 7.", "Beräkna x y = 7."),
        ("Temperaturen är -7 grader.", "Temperaturen är 7 grader."),
        ("Lös x=-7.", "Lös x=7."),
        ("Förenkla -(x + y).", "Förenkla (x + y)."),
        ("Beräkna x - sin(y).", "Beräkna x sin(y)."),
        ("Förenkla -sin(x).", "Förenkla sin(x)."),
    ],
    ids=[
        "formula",
        "reversed-sentence",
        "one-letter-word",
        "minus",
        "unicode-minus",
        "negative-number",
        "sign-after-equals",
        "sign-before-bracket",
        "minus-before-function",
        "sign-before-function",
    ],
)
def test_a_dropped_paragraph_is_flagged_even_when_the_item_shares_its_words(dropped, kept):
    state = _state(dropped, kept)

    admit_batch(
        {"items": [_item(["body:0002"], body=[{"segments": [_text(kept)]}])]},
        state,
    )

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, dropped)


def test_a_dropped_stem_read_through_its_gap_answer_is_not_flagged():
    stem = "1. The bands ____ (spelar) at the festival."
    state = _state("Fyll i rätt form.", stem)
    body: JsonValue = [
        {"segments": [_text("Fyll i rätt form.")]},
        {
            "segments": [
                _text("The bands "),
                {
                    "kind": "gap",
                    "text": None,
                    "accepted_values": ["play"],
                },
                _text(" (spelar) at the festival."),
            ]
        },
    ]

    admit_batch(
        {"items": [_item(["body:0001"], kind="gap_fill", key_source="invented", body=body)]}, state
    )

    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
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
                _item(
                    ["body:0001"],
                    kind="single_choice",
                    key_source="invented",
                    choices=choices,
                    criteria=[],
                )
            ]
        },
        state,
    )

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.reasons == ()


def test_a_dropped_bullet_list_of_options_is_read_without_its_bullets():
    options = "- play\n- plays"
    state = _state(_STEM, options)
    choices: list[JsonValue] = [
        {"text": "play", "correct": True},
        {"text": "plays", "correct": False},
    ]

    admit_batch(
        {
            "items": [
                _item(
                    ["body:0001"],
                    kind="single_choice",
                    key_source="invented",
                    choices=choices,
                    criteria=[],
                )
            ]
        },
        state,
    )

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.reasons == ()


@pytest.mark.parametrize(
    "stem",
    ["absence without permission", "absence without permission: truancy"],
    ids=["one-cell-repeated", "every-cell-repeated"],
)
def test_a_dropped_table_the_stem_repeats_is_flagged(stem):
    # The stem paragraph is aligned to the stem chunk; repeating the table's words never
    # shows the table chunk (TASK-SKRIPT-39-04-14 D4).
    table = "1. absence without permission | ____ | A. truancy"
    state = _state(stem, table)

    admit_batch({"items": [_item(["body:0001"], body=[{"segments": [_text(stem)]}])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.reasons == (LEFT_OUT_REASON, table)


def test_a_dropped_stem_whose_words_span_text_segments_is_not_flagged():
    stem = "Vilket ord är ett substantiv?"
    state = _state("Läs meningen.", stem)
    body: JsonValue = [
        {"segments": [_text("Läs meningen.")]},
        {"segments": [_text("Vilket ord är ett sub"), _text("stantiv?")]},
    ]

    admit_batch({"items": [_item(["body:0001"], body=body)]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.reasons == ()


def test_a_points_label_split_across_text_segments_leaves_the_stem():
    stem = "Vilket ord är ett substantiv? (1 p)"
    state = _state(stem)
    body: JsonValue = [{"segments": [_text("Vilket ord är ett substantiv? (1"), _text(" p)")]}]

    admit_batch({"items": [_item(["body:0001"], body=body, points=None)]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
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
                    key_source="invented",
                    body=[{"segments": [_text(stem)]}],
                    points=None,
                    choices=choices,
                    criteria=[],
                )
            ]
        },
        state,
    )

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.points == 1
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
                    key_source="invented",
                    body=[{"segments": [_text(texts[0])]}],
                    points=None,
                    choices=choices,
                    criteria=[],
                )
            ]
        },
        state,
    )

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.points is None
    assert _stem_texts(admitted) == [texts[0]]


def test_points_the_reply_gives_win_over_a_printed_label():
    stem = "Vilket ord är ett substantiv? (1 p)"
    state = _state(stem)

    admit_batch({"items": [_item(["body:0001"], body=[{"segments": [_text(stem)]}])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
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
                    key_source="invented",
                    body=[{"segments": [_text("Vilket ord är ett substantiv?")]}],
                    points=None,
                    choices=choices,
                    criteria=[],
                )
            ]
        },
        state,
    )

    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.points == 1
    assert anchors[-1] == "body:0004"
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()
