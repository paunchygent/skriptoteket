"""Carrier decisions apply to omitted source, never model-emitted content."""

import random

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

pytestmark = pytest.mark.unit


def chunk(anchor, text):
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        runs=(DocxSourceRun(0, text, ("bold",)),),
        paragraphs=(DocxSourceParagraph(0, text, None),),
    )


def convert(source, wordings, *, points=2, prompt="Choose.", source_prompt=None):
    source_parts = [source] if isinstance(source, str) else source
    chunks = (
        chunk("body:0001", prompt if source_prompt is None else source_prompt),
        *(chunk(f"body:{index:04d}", part) for index, part in enumerate(source_parts, start=2)),
    )
    produced = ProducedItem.model_validate(
        {
            "source_anchors": [c.anchor for c in chunks],
            "outcome": "converted",
            "review_reason": None,
            "kind": "single_choice",
            "printed_label": None,
            "points": points,
            "facit_text": None,
            "key_source": None,
            "body": [{"segments": [{"kind": "text", "text": prompt, "accepted_values": []}]}],
            "choices": [{"text": text, "correct": False} for text in wordings],
        }
    )
    return native_item(produced, chunks=chunks, language="en")


@pytest.mark.parametrize(
    "wording",
    [
        "Write answer key: literally.",
        "Type Svar: followed by your name.",
        "Discuss the answer key: explain its purpose.",
        "Simplify q(2 p)",
        "Evaluate f(2 p)",
        "Calculate (2 p)",
        "Explain why the team earned 2 points",
    ],
)
def test_reviewer_emitted_literals_are_preserved(wording):
    result = convert("A. red B. " + wording, ["red", wording])
    assert body_plain_text(result.choices[1].body) == wording


def test_emitted_ordinal_like_prefix_is_visible_content_with_its_marks():
    result = convert("a) is a literal. blue", ["a) is a literal.", "blue"])
    assert body_plain_text(result.choices[0].body) == "a) is a literal."
    assert all(
        segment.marks == ("bold",)
        for paragraph in result.choices[0].body
        for segment in paragraph.segments
    )


@pytest.mark.parametrize("wording", ["Simplify q(2 p)", "Write answer key: literally."])
def test_model_emitted_question_body_is_not_carrier_content(wording):
    result = convert("A. red B. blue", ["red", "blue"], prompt=wording)
    assert body_plain_text(result.body) == wording


@pytest.mark.parametrize(
    "tail",
    [
        "Svar:\nThe correct option is B.",
        "Svar: blue\nThe correct option is B.\nAn explanation continues.",
    ],
)
def test_reviewer_multiline_answer_is_excluded(tail):
    result = convert("A. red B. blue\n" + tail, ["red", "blue"])
    assert [body_plain_text(c.body) for c in result.choices] == ["red", "blue"]
    assert result.facit_text is None


def test_reviewer_separate_answer_paragraphs_are_excluded():
    result = convert(["A. red B. blue", "Svar:", "The correct option is B."], ["red", "blue"])
    assert [body_plain_text(c.body) for c in result.choices] == ["red", "blue"]
    assert result.facit_text is None


def test_reviewer_score_inside_first_entry_is_excluded():
    result = convert("A. red (2 p) B. blue", ["red", "blue"])
    assert [body_plain_text(c.body).strip() for c in result.choices] == ["red", "blue"]


@pytest.mark.parametrize(
    "source",
    [
        "A. (2 p) red B. blue",
        "A. red B. (2 p) blue",
        "A. red B. blue\n(2 p)",
    ],
)
def test_recovered_score_placement_does_not_change_visible_content(source):
    result = convert(source, ["red", "blue"])
    assert [body_plain_text(c.body).strip() for c in result.choices] == ["red", "blue"]


@pytest.mark.parametrize("tail", ["(2 p)", "Svar:\nprivate_answer"])
def test_recovered_carriers_cannot_force_deletion_of_model_insertions(tail):
    result = convert("A. red B. blue " + tail, ["red", "blue extra"])
    assert body_plain_text(result.choices[1].body) == "blue extra"
    assert result.facit_text is None


@pytest.mark.parametrize("points", [2, None])
def test_omitted_points_not_corresponding_to_native_field_are_visible(points):
    result = convert("A. red B. blue (7 p)", ["red", "blue"], points=points)
    assert "(7 p)" in body_plain_text(result.choices[1].body)


@pytest.mark.parametrize("tail", ["(2 p)", "Svar:\nprivate_answer"])
def test_inserted_word_suffix_is_preserved_beside_recovered_carriers(tail):
    result = convert("A. red " + tail + " B. blue", ["reddish", "blue"])
    assert body_plain_text(result.choices[0].body) == "reddish"
    assert [segment.marks for p in result.choices[0].body for segment in p.segments] == [
        ("bold",),
        (),
    ]


def test_inserted_punctuation_inside_a_word_is_not_lost_to_score_recovery():
    result = convert("A. red (2 p) B. blue", ["r-ed", "blue"])
    assert body_plain_text(result.choices[0].body) == "r-ed"


def test_question_body_word_insertion_is_preserved_beside_recovered_score():
    result = convert(
        "A. blue B. green",
        ["blue", "green"],
        prompt="reddish",
        source_prompt="red (2 p)",
    )
    assert body_plain_text(result.body) == "reddish"


def test_more_model_alternatives_than_source_words_preserves_every_alternative():
    result = convert("red", ["red", "blue", "green"])
    assert [body_plain_text(c.body) for c in result.choices] == ["red", "blue", "green"]
    assert result.facit_text is None


def test_seeded_emitted_content_and_null_answer_properties():
    rng = random.Random(3909085)
    labels = ["Svar:", "answer key:", "Answer:"]
    quotes = [("", ""), ('"', '"'), ("«", "»"), ("”", "”"), ("'", "'")]
    for case in range(160):
        opening, closing = rng.choice(quotes)
        point = rng.choice(["q(2 p)", "(2 p)", "2 points"])
        tokens = [
            "Show",
            opening + rng.choice(labels) + closing,
            opening + point + closing,
            "«A. is literal»",
            "literally",
        ]
        rng.shuffle(tokens)
        wording = rng.choice([" ", "\n"]).join(tokens) + rng.choice(["", ".", "!"])
        printed = rng.choice([True, False])
        rewritten = rng.choice([True, False])
        first_source = "Identify the shared red concept." if rewritten else "red"
        first_model = "The shared red concept." if rewritten else "red"
        source = (("A. " + first_source + " B. ") if printed else (first_source + "\n")) + wording
        answer = f"private_answer_{case}"
        score = rng.choice(["", " (2 p)", "\n(2 p)"])
        source += score + rng.choice([" ", "\n"]) + "Svar:\n" + answer + "\nTeacher explanation."
        result = convert(source, [first_model, wording])
        visible = [body_plain_text(c.body) for c in result.choices]
        assert visible == [first_source, wording], (case, source, visible)
        assert answer not in "\n".join(visible)
        assert result.facit_text is None
