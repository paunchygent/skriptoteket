"""Source text the facit repeats is shared wording with unknown ownership (REP-0049 F4).

Exact containment proves the wording is shared, not that the key owns it, so such
spans are never carriers: a rebuild that would show one sends the item to review
instead (rereview F4, decision A). The detection keeps its word-boundary, emitted
and partly-emitted gap rules.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.source_native_carriers import (
    emitted_positions,
    facit_shared_spans,
    native_carrier_spans,
)

pytestmark = pytest.mark.unit


def test_one_facit_sentence_at_a_paragraphs_end_becomes_one_span():
    text = "2. Klassen läste inte texten. Analys: Klassen (S) läste (P)."
    facit = "Klassen (S) läste (P)."
    emitted = emitted_positions(text, "Klassen läste inte texten. Analys:")

    spans = facit_shared_spans(
        text,
        facit=facit,
        emitted=emitted,
        search=((0, len(text)),),
    )

    assert spans == ((text.index("Klassen (S)"), len(text)),)


def test_three_facit_sentences_in_three_source_paragraphs_become_three_spans():
    text = (
        "a) Klassen läste inte texten. Analys: Klassen (S) läste."
        "\nb) Mentorn skrev brevet. Analys: Mentorn (S) skrev."
        "\nc) Dagen blev stressig. Analys: Dagen (S) blev."
    )
    facit = "Klassen (S) läste. Mentorn (S) skrev. Dagen (S) blev."
    emitted = emitted_positions(
        text,
        "a) Klassen läste inte texten. Analys:"
        "\nb) Mentorn skrev brevet. Analys:"
        "\nc) Dagen blev stressig. Analys:",
    )

    spans = facit_shared_spans(
        text,
        facit=facit,
        emitted=emitted,
        search=((0, len(text)),),
    )

    assert spans == (
        (text.index("Klassen (S)"), text.index("läste.") + len("läste.")),
        (text.index("Mentorn (S)"), text.index("skrev.") + len("skrev.")),
        (text.index("Dagen (S)"), len(text)),
    )


def test_a_facit_sentence_the_reply_body_emitted_is_no_shared_span():
    text = "2. Klassen läste inte texten. Analys: Klassen (S) läste (P)."
    facit = "Klassen (S) läste (P)."
    emitted = emitted_positions(text, "Klassen läste inte texten. Klassen (S) läste (P).")

    spans = facit_shared_spans(
        text,
        facit=facit,
        emitted=emitted,
        search=((0, len(text)),),
    )

    assert spans == ()


def test_a_single_facit_word_inside_a_longer_source_word_is_no_shared_span():
    text = "2. Skriv äpplekaka."
    emitted = emitted_positions(text, "Skriv.")

    spans = facit_shared_spans(
        text,
        facit="äpple",
        emitted=emitted,
        search=((0, len(text)),),
    )

    assert spans == ()


def test_a_facit_sentence_restating_an_emitted_question_beside_a_gap_is_no_shared_span():
    text = "a) De nyfikna barnen Frastyp: NF\nb) skulle springa Frastyp: VF"
    emitted = emitted_positions(text, "a) De nyfikna barnen Frastyp: \nb) skulle springa Frastyp: ")

    spans = facit_shared_spans(
        text,
        facit="a) De nyfikna barnen Frastyp: NF\nb) skulle springa Frastyp: VF",
        emitted=emitted,
        search=((0, len(text)),),
    )

    assert spans == ()


def test_italic_tags_in_the_facit_still_match_the_plain_source():
    text = "2. Klassen läste inte texten. Analys: Klassen (S) läste (P)."
    emitted = emitted_positions(text, "Klassen läste inte texten. Analys:")

    spans = facit_shared_spans(
        text,
        facit="<i>Klassen (S)</i> läste (P).",
        emitted=emitted,
        search=((0, len(text)),),
    )

    assert spans == ((text.index("Klassen (S)"), len(text)),)


def test_native_carriers_no_longer_return_facit_spans():
    text = "2. Klassen läste inte texten. Analys: Klassen (S) läste (P)."
    emitted = emitted_positions(text, "Klassen läste inte texten. Analys:")
    regions = ((0, len(text)),)

    assert native_carrier_spans(text, emitted=emitted, regions=regions) == ()
