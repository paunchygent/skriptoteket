"""A converted item marks a listed own chunk that no paragraph, choice or entry shows.

The listed-chunk check covers every own chunk of the question the item itself lists
(TASK-SKRIPT-39-04-15 D1): a listed word bank, listed shown chunk, listed facit line,
listed points line, listed governing chunk, listed section instruction, blank answer
lines, and a listed plus an unlisted chunk together. A listed source answer or facit
line, points line, grouped key, governing chunk, header or section-placed instruction is
never marked (D2); the alignment says what the item shows, never the reply's wording.
"""

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_left_out_test_support import (
    _STEM,
    _item,
    _state,
    _text,
)

pytestmark = pytest.mark.unit

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
