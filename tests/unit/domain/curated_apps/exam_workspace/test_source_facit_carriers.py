"""Source text the facit copies verbatim is a recovered key carrier (REP-0049 F3/F1).

The reply contract keeps the teacher's facit wording verbatim while text segments never
carry inline facit, so source text the facit copies, and that the reply did not emit, owns
its span exactly like a recovered answer label does.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.source_native_carriers import (
    emitted_positions,
    native_carrier_spans,
)

pytestmark = pytest.mark.unit


def test_one_facit_sentence_at_a_paragraphs_end_becomes_one_span():
    text = "2. Klassen läste inte texten. Analys: Klassen (S) läste (P)."
    facit = "Klassen (S) läste (P)."
    emitted = emitted_positions(text, "Klassen läste inte texten. Analys:")

    spans = native_carrier_spans(
        text,
        emitted=emitted,
        regions=((0, len(text)),),
        facit=facit,
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

    spans = native_carrier_spans(
        text,
        emitted=emitted,
        regions=((0, len(text)),),
        facit=facit,
    )

    assert spans == (
        (text.index("Klassen (S)"), text.index("läste.") + len("läste.")),
        (text.index("Mentorn (S)"), text.index("skrev.") + len("skrev.")),
        (text.index("Dagen (S)"), len(text)),
    )


def test_a_facit_sentence_the_reply_body_emitted_is_no_carrier():
    text = "2. Klassen läste inte texten. Analys: Klassen (S) läste (P)."
    facit = "Klassen (S) läste (P)."
    emitted = emitted_positions(text, "Klassen läste inte texten. Klassen (S) läste (P).")

    spans = native_carrier_spans(
        text,
        emitted=emitted,
        regions=((0, len(text)),),
        facit=facit,
    )

    assert spans == ()


def test_a_single_facit_word_inside_a_longer_source_word_is_no_carrier():
    text = "2. Skriv äpplekaka."
    emitted = emitted_positions(text, "Skriv.")

    spans = native_carrier_spans(
        text,
        emitted=emitted,
        regions=((0, len(text)),),
        facit="äpple",
    )

    assert spans == ()


def test_a_facit_sentence_restating_an_emitted_question_beside_a_gap_is_no_carrier():
    text = "a) De nyfikna barnen Frastyp: NF\nb) skulle springa Frastyp: VF"
    emitted = emitted_positions(text, "a) De nyfikna barnen Frastyp: \nb) skulle springa Frastyp: ")

    spans = native_carrier_spans(
        text,
        emitted=emitted,
        regions=((0, len(text)),),
        facit="a) De nyfikna barnen Frastyp: NF\nb) skulle springa Frastyp: VF",
    )

    assert spans == ()


def test_facit_none_changes_nothing():
    text = "2. Klassen läste inte texten. Analys: Klassen (S) läste (P)."
    emitted = emitted_positions(text, "Klassen läste inte texten. Analys:")
    regions = ((0, len(text)),)

    assert native_carrier_spans(
        text, emitted=emitted, regions=regions, facit=None
    ) == native_carrier_spans(text, emitted=emitted, regions=regions)


def test_italic_tags_in_the_facit_still_match_the_plain_source():
    text = "2. Klassen läste inte texten. Analys: Klassen (S) läste (P)."
    emitted = emitted_positions(text, "Klassen läste inte texten. Analys:")

    spans = native_carrier_spans(
        text,
        emitted=emitted,
        regions=((0, len(text)),),
        facit="<i>Klassen (S)</i> läste (P).",
    )

    assert spans == ((text.index("Klassen (S)"), len(text)),)
