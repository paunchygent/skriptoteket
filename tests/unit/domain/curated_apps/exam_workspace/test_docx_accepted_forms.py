"""Accepted answer forms a gap gains, judged against the fresh live recordings.

``with_accepted_forms`` only adds forms: the parts of a facit value that joins alternatives
with a slash, both halves of a "short = term" definition the item's context prints, the
keyboard spelling of a typographic apostrophe, and the other closing stop of a sentence
form. No model value is removed or duplicated. Through admission (D13) a gap whose facit
gives one half accepts both.
"""

from collections.abc import Callable

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    defined_short_forms,
    definition_context,
    with_accepted_forms,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
    recorded_produced_items,
)

pytestmark = pytest.mark.unit

_GRAMMAR = (
    "svenska_2_grammatik_omprov_variant_1_med_facit",
    "svenska_2_grammatik_omprov_variant_2_med_facit",
)
_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"
_DIAGNOSTIC = "bf26_diagnostic_grammar_test_ht26_med_facit"

# The section instruction defines each abbreviation and its term; the two live grammar exams
# return the terms in one item and the abbreviations in another.
_DEFINED_ITEM = "body:0037"
_ABBREVIATED_ITEM = "body:0008"
_UNDEFINED_ITEM = "body:0016"


def _gaps(item: ProducedItem) -> list[tuple[str, ...]]:
    return [
        segment.accepted_values
        for p in item.body
        for segment in p.segments
        if segment.kind == "gap"
    ]


def _flat_gaps(item: ProducedItem) -> set[str]:
    return {value for values in _gaps(item) for value in values}


def _recorded(exam: str, anchor: str) -> ProducedItem:
    return next(item for item in recorded_produced_items(exam) if item.source_anchors[0] == anchor)


def _context(exam: str, item: ProducedItem) -> tuple[DocxChunk, ...]:
    return definition_context(tuple(chunks_by_anchor(exam).values()), item.source_anchors)


def _definitions(context: tuple[DocxChunk, ...]) -> dict[str, str]:
    return dict(defined_short_forms(chunk.text for chunk in context))


def _without(item: ProducedItem, dropped: Callable[[str], bool]) -> ProducedItem:
    """The item with every accepted value ``dropped`` returns True for removed."""
    body = tuple(
        paragraph.model_copy(
            update={
                "segments": tuple(
                    segment.model_copy(
                        update={
                            "accepted_values": tuple(
                                value for value in segment.accepted_values if not dropped(value)
                            )
                        }
                    )
                    if segment.kind == "gap"
                    else segment
                    for segment in paragraph.segments
                )
            }
        )
        for paragraph in item.body
    )
    return item.model_copy(update={"body": body})


@pytest.mark.parametrize("exam", _GRAMMAR)
@pytest.mark.parametrize("anchor", [_DEFINED_ITEM, _ABBREVIATED_ITEM])
def test_a_defined_half_of_a_facit_form_accepts_the_other_half(exam: str, anchor: str):
    item = _recorded(exam, anchor)
    context = _context(exam, item)
    definitions = _definitions(context)
    assert {"Adv", "DO", "IO", "Pf", "R", "A", "B"} & set(definitions)

    widened = with_accepted_forms(item, context)

    for original, values in zip(_gaps(item), _gaps(widened), strict=True):
        assert set(original) <= set(values)
        for value in original:
            for short, term in definitions.items():
                if value.casefold() == short.casefold():
                    assert term in values, (anchor, value)
                if value.casefold() == term.casefold():
                    assert short in values, (anchor, value)


@pytest.mark.parametrize("exam", _GRAMMAR)
def test_a_short_form_the_context_does_not_define_is_left_alone(exam: str):
    item = _recorded(exam, _UNDEFINED_ITEM)
    context = _context(exam, item)
    # The lines above print the R = rotmorfem definitions, so NF, PF and VF match none.
    assert _definitions(context)

    widened = with_accepted_forms(item, context)

    assert _gaps(widened) == _gaps(item)


@pytest.mark.parametrize("exam", _GRAMMAR)
def test_a_facit_value_joining_alternatives_with_a_slash_accepts_each_part(exam: str):
    item = _recorded(exam, _DEFINED_ITEM)
    joined = [value for values in _gaps(item) for value in values if "/" in value]
    assert joined

    widened = with_accepted_forms(item, _context(exam, item))

    for value in joined:
        assert set(value.split("/")) <= _flat_gaps(widened)


@pytest.mark.parametrize("exam", _GRAMMAR)
def test_a_facit_that_already_names_both_halves_keeps_them_once(exam: str):
    item = _recorded(exam, _DEFINED_ITEM)
    definitions = _definitions(_context(exam, item))
    by_term = {term: short for short, term in definitions.items()}

    def paired(values: tuple[str, ...]) -> tuple[str, ...]:
        both: list[str] = []
        for value in values:
            if value in definitions:
                both.extend((value, definitions[value]))
            elif value in by_term:
                both.extend((by_term[value], value))
            else:
                both.append(value)
        return tuple(both)

    body = tuple(
        paragraph.model_copy(
            update={
                "segments": tuple(
                    segment.model_copy(update={"accepted_values": paired(segment.accepted_values)})
                    if segment.kind == "gap"
                    else segment
                    for segment in paragraph.segments
                )
            }
        )
        for paragraph in item.body
    )
    padded = item.model_copy(update={"body": body})
    assert _flat_gaps(padded) > _flat_gaps(item)

    widened = with_accepted_forms(padded, _context(exam, item))

    for original, values in zip(_gaps(padded), _gaps(widened), strict=True):
        assert set(original) <= set(values)
        assert len(values) == len(set(values))


def test_a_facit_spelled_with_a_typographic_apostrophe_also_accepts_the_keyboard_form():
    item = _recorded(_ENGLISH, "body:0109")
    curly = [value for values in _gaps(item) for value in values if "\u2019" in value]
    assert curly
    keyboard = {value.replace("\u2019", "'") for value in curly}
    stripped = _without(item, lambda value: value in keyboard)
    assert not keyboard & _flat_gaps(stripped)

    widened = with_accepted_forms(stripped, ())

    assert keyboard <= _flat_gaps(widened)
    for original, values in zip(_gaps(stripped), _gaps(widened), strict=True):
        assert set(original) <= set(values)


def test_a_sentence_facit_is_accepted_with_and_without_its_closing_stop():
    item = _recorded(_DIAGNOSTIC, "body:0015")
    sentences = [value for values in _gaps(item) for value in values if len(value.split()) >= 3]
    assert sentences
    without_stop = {value.rstrip(".") for value in sentences}
    stripped = _without(item, lambda value: value in without_stop)

    widened = with_accepted_forms(stripped, ())

    assert without_stop <= _flat_gaps(widened)
    for original, values in zip(_gaps(stripped), _gaps(widened), strict=True):
        assert set(original) <= set(values)


@pytest.mark.asyncio
@pytest.mark.parametrize("exam", _GRAMMAR)
async def test_admitted_gaps_accept_both_halves_of_the_definition_in_their_context(exam: str):
    replay = build_replay(exam)
    outcome = await replay.pipeline.convert(job=replay.job())
    assert not [event for event in outcome.result.events if event.stage != "formatting"], exam

    document = outcome.result.document
    for anchor in (_DEFINED_ITEM, _ABBREVIATED_ITEM):
        definitions = _definitions(_context(exam, _recorded(exam, anchor)))
        assert definitions
        item = next(item for item in document.items if item.source_anchor == anchor)
        for gap in item.gaps:
            values = set(gap.accepted_values)
            for value in values:
                for short, term in definitions.items():
                    if value.casefold() == short.casefold():
                        assert term in values, (exam, anchor, value)
                    if value.casefold() == term.casefold():
                        assert short in values, (exam, anchor, value)
