"""A converted item holds the own chunks of its question that the reply leaves out (D41). Only a
chunk no body paragraph, choice or matching entry is aligned to shows under the item's check
mark as printed; a source answer or facit line is never marked (D4, TASK-SKRIPT-39-04-14). A
reply without points takes the one points label the item's own chunks print, and the label
leaves the stem (D3)."""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
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

pytestmark = pytest.mark.unit

_STEM = "1. Beskriv kort hur en intervju planeras."
_FACIT = "Svar: syfte, urval och frågor bestäms i förväg."


def _chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _state(*texts: str, grouped_keys: frozenset[str] = frozenset()) -> DocxBuildState:
    chunks = tuple(_chunk(f"body:{n:04d}", text) for n, text in enumerate(texts, start=1))
    return DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(tuple(c.anchor for c in chunks),),
        grouped_keys=grouped_keys,
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
        "key_source": None,
        "facit_text": None,
        "printed_label": "1",
        "body": [{"segments": [_text(_STEM[3:])]}],
        "points": 2,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
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


_WORD_BANK = "Använd orden: rim, meter, strof"


def _left_out_events(state: DocxBuildState) -> list[tuple[int | None, tuple[str, ...]]]:
    return [
        (event.item, event.anchors) for event in state.events if event.code == "own_chunks_left_out"
    ]


def test_a_listed_own_chunk_no_paragraph_shows_is_flagged():
    # The item lists the word bank, but its body shows only the stem: the listed chunk is no
    # body paragraph's, no choice's and no matching entry's, so it is marked (D1, D2).
    state = _state(_STEM, _WORD_BANK)

    admit_batch({"items": [_item(["body:0001", "body:0002"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, _WORD_BANK)
    assert _left_out_events(state) == [(0, ("body:0002",))]


def test_a_listed_own_chunk_a_body_paragraph_shows_is_not_flagged_even_reworded():
    # A listed chunk a body paragraph is aligned to is shown: no wording comparison (D7).
    state = _state(_STEM)

    body: JsonValue = [{"segments": [_text("Beskriv kort hur intervjun planeras.")]}]
    admit_batch({"items": [_item(["body:0001"], body=body)]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.reasons == ()
    assert _left_out_events(state) == []


def test_a_listed_facit_line_no_paragraph_shows_is_not_flagged():
    facit = "Correct answer: A. rhyme scheme"
    state = _state(_STEM, facit)

    admit_batch({"items": [_item(["body:0001", "body:0002"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()
    assert _left_out_events(state) == []


def test_a_listed_points_line_no_paragraph_shows_is_not_flagged():
    state = _state(_STEM, "(1 p)")

    admit_batch({"items": [_item(["body:0001", "body:0002"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.reasons == ()
    assert _left_out_events(state) == []


def test_a_listed_governing_chunk_no_paragraph_shows_is_not_flagged():
    state = _state(_STEM, _WORD_BANK)
    state.governing = frozenset({"body:0002"})

    admit_batch({"items": [_item(["body:0001", "body:0002"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.reasons == ()
    assert _left_out_events(state) == []


def test_a_listed_chunk_a_section_instruction_lists_is_not_flagged():
    state = _state(_STEM, _WORD_BANK)
    state.instructions = (ProducedMetadata(text=_WORD_BANK, source_anchors=("body:0002",)),)

    admit_batch({"items": [_item(["body:0001", "body:0002"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.reasons == ()
    assert _left_out_events(state) == []


def test_an_unlisted_and_a_listed_left_out_chunk_are_one_event_in_source_order():
    # The lead is left out and unlisted; the word bank is listed but no paragraph shows it.
    # One event names both in source order and the mark shows both (D1).
    lead = "Läs dikten nedan."
    state = _state(lead, _STEM, _WORD_BANK)

    admit_batch({"items": [_item(["body:0002", "body:0003"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, lead, _WORD_BANK)
    assert _left_out_events(state) == [(0, ("body:0001", "body:0003"))]


def test_a_listed_blank_answer_line_no_paragraph_shows_is_not_flagged():
    # A blank answer line is the response space the item's gap or answer field takes, so no
    # paragraph shows it yet it is no left-out text (D2).
    state = _state(_STEM, "________________")

    admit_batch({"items": [_item(["body:0001", "body:0002"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()
    assert _left_out_events(state) == []


def test_an_unlisted_blank_answer_line_no_paragraph_shows_is_not_flagged():
    state = _state(_STEM, "________________")

    admit_batch({"items": [_item(["body:0001"])]}, state)

    ((admitted, anchors),) = [(a.item, h) for a, h in state.accepted]
    assert anchors == ("body:0001", "body:0002")
    assert admitted.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert admitted.review.reasons == ()
    assert _left_out_events(state) == []


def test_a_listed_word_bank_next_to_a_listed_blank_line_marks_only_the_word_bank():
    state = _state(_STEM, _WORD_BANK, "________________")

    admit_batch({"items": [_item(["body:0001", "body:0002", "body:0003"])]}, state)

    ((admitted, _),) = [(a.item, h) for a, h in state.accepted]
    assert admitted.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert admitted.review.reasons == (LEFT_OUT_REASON, _WORD_BANK)
    assert _left_out_events(state) == [(0, ("body:0002",))]
