"""Joint ownership survives rewrites and repeated words without occurrence products."""

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


def _convert(text, *, choices=(), left=(), right=()):
    prompt = "Choose an answer."
    chunks = (
        DocxChunk("body:0001", "paragraph", prompt, prompt),
        DocxChunk(
            "body:0002",
            "paragraph",
            text,
            text,
            runs=(DocxSourceRun(0, text, ("bold",)),),
            paragraphs=(DocxSourceParagraph(0, text, None),),
        ),
    )
    item = ProducedItem.model_validate(
        {
            "source_anchors": [chunk.anchor for chunk in chunks],
            "outcome": "converted",
            "review_reason": None,
            "kind": "matching" if left else "single_choice",
            "body": [{"segments": [{"kind": "text", "text": prompt, "accepted_values": []}]}],
            "key_source": None,
            "facit_text": None,
            "points": 2,
            "choices": [{"text": text, "correct": False} for text in choices],
            "match_left": left,
            "match_right": right,
        }
    )
    result = native_item(item, chunks=chunks, language="en")
    assert body_plain_text(result.body) == prompt
    assert result.facit_text is None
    assert all(isinstance(entry.body, tuple) for entry in result.choices)
    assert all(isinstance(entry.body, tuple) for entry in result.match_left)
    assert all(isinstance(entry.body, tuple) for entry in result.match_right)
    return result


@pytest.mark.parametrize(
    "choices",
    [
        ("Describe the important concept.", "State the crucial idea."),
        ("Qxz", "Jkw"),
    ],
)
def test_all_rewritten_choices_rebuild_their_disjoint_whole_source_words(choices):
    result = _convert(
        "A. Identify the important concept. B. Explain the crucial idea.",
        choices=choices,
    )
    assert [body_plain_text(entry.body) for entry in result.choices] == [
        "Identify the important concept.",
        "Explain the crucial idea.",
    ]
    assert all(
        segment.marks == ("bold",)
        for entry in result.choices
        for paragraph in entry.body
        for segment in paragraph.segments
    )


@pytest.mark.parametrize(
    "left,right",
    [
        (("reddish", "bluish"), ("warmish", "coldish")),
        (("Qxz", "Jkw"), ("Pvn", "Ztf")),
        (("Qxz", "blue"), ("Pvn", "cold")),
    ],
)
def test_all_surfaces_share_the_partition_even_without_exact_wording(left, right):
    result = _convert("1. red A. warm 2. blue B. cold", left=left, right=right)
    inserted_suffixes = left == ("reddish", "bluish")
    assert [body_plain_text(entry.body) for entry in result.match_left] == [
        "reddish" if inserted_suffixes else "red",
        "blue",
    ]
    assert [body_plain_text(entry.body) for entry in result.match_right] == (
        ["warmish", "coldish"] if inserted_suffixes else ["warm", "cold"]
    )
    segments = [
        [
            (segment.text, segment.marks)
            for paragraph in entry.body
            for segment in paragraph.segments
        ]
        for entry in (*result.match_left, *result.match_right)
    ]
    assert segments == (
        [
            [("red", ("bold",)), ("dish", ())],
            [("blue", ("bold",))],
            [("warm", ("bold",)), ("ish", ())],
            [("cold", ("bold",)), ("ish", ())],
        ]
        if inserted_suffixes
        else [[(word, ("bold",))] for word in ("red", "blue", "warm", "cold")]
    )


def _letters(value):
    text = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        text = chr(65 + remainder) + text
    return text


@pytest.mark.parametrize("count", [8, 16, 24, 32, 40])
def test_printed_labels_resolve_every_duplicate_to_its_own_entry(count):
    text = " ".join(f"{i}. same {_letters(i)}. same" for i in range(1, count + 1))
    result = _convert(text, left=["same"] * count, right=["same"] * count)
    assert [body_plain_text(entry.body) for entry in result.match_left] == ["same"] * count
    assert [body_plain_text(entry.body) for entry in result.match_right] == ["same"] * count
