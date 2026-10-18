"""Adversarial source-entry partition variants beyond the R6/R9 reviewer probes.

Every case drives the real ``aligned_native_item`` assembly and asserts which source
characters each entry owns: the complete source wording, its source marks, and
no neighbour's words. Unlabelled rewrites deliberately keep word evidence for
their own sentence (usually its first and last word) so the intended sentence
is the unique best alignment rather than a guess.
"""

import re

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.domain.curated_apps.exam_workspace.test_source_entry_partition_repair3 import (
    _convert,
)

pytestmark = pytest.mark.unit

_BOLD = ("bold",)
_SENTENCES = (
    "Identify the important concept.",
    "Explain the crucial idea.",
    "Summarize the central theme.",
    "Describe the primary method.",
    "Compare the secondary result.",
)
_REWRITES = (
    "Identify the vital concept.",
    "Explain the essential idea.",
    "Summarize the principal theme.",
    "Describe the leading method.",
    "Compare the alternate result.",
)
_MIXED_EXACT = {
    3: (False, True, False),
    4: (True, False, True, False),
    5: (False, True, False, True, False),
}
_WORD = re.compile(r"[^\W_]+")


def _convert_runs(runs, *, choices=(), left=(), right=()):
    """One item whose entry paragraph carries explicit ``(text, marks)`` runs."""
    text = "".join(piece for piece, _ in runs)
    compiled: list[DocxSourceRun] = []
    offset = 0
    for piece, marks in runs:
        assert text[offset : offset + len(piece)] == piece
        compiled.append(DocxSourceRun(offset, piece, tuple(marks)))
        offset += len(piece)
    assert offset == len(text)
    prompt = "Choose an answer."
    chunks = (
        DocxChunk("body:0001", "paragraph", prompt, prompt),
        DocxChunk(
            "body:0002",
            "paragraph",
            text,
            text,
            runs=tuple(compiled),
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
            "choices": [{"text": value, "correct": False} for value in choices],
            "match_left": left,
            "match_right": right,
        }
    )
    result = aligned_native_item(item, chunks=chunks, language="en").item
    assert body_plain_text(result.body) == prompt
    assert result.facit_text is None
    assert all(isinstance(entry.body, tuple) for entry in result.choices)
    assert all(isinstance(entry.body, tuple) for entry in result.match_left)
    assert all(isinstance(entry.body, tuple) for entry in result.match_right)
    return result


def _bodies(entries):
    return [body_plain_text(entry.body).strip() for entry in entries]


def _segments(entries):
    return [
        [
            (segment.text, tuple(segment.marks))
            for paragraph in entry.body
            for segment in paragraph.segments
        ]
        for entry in entries
    ]


def _assert_source_entries(entries, expected, *, marks=_BOLD):
    """Each entry carries its whole expected source wording with its marks."""
    assert _bodies(entries) == list(expected)
    assert _segments(entries) == [[(text, tuple(marks))] for text in expected]


def _assert_no_foreign_words(entries, expected):
    """No entry carries a word that only another entry's source sentence has."""
    bodies = _bodies(entries)
    words = [set(_WORD.findall(text.casefold())) for text in expected]
    for index, body in enumerate(bodies):
        foreign = set().union(*(own for other, own in enumerate(words) if other != index))
        foreign -= words[index]
        assert not (set(_WORD.findall(body.casefold())) & foreign)


@pytest.mark.parametrize("count", (3, 4, 5))
def test_no_label_mixed_exact_and_rewritten_neighbours_own_whole_sentences(count):
    exact = _MIXED_EXACT[count]
    source = " ".join(_SENTENCES[:count])
    model = tuple(
        sentence if is_exact else _REWRITES[index]
        for index, (sentence, is_exact) in enumerate(zip(_SENTENCES[:count], exact, strict=True))
    )
    result = _convert(source, choices=model)
    expected = _SENTENCES[:count]
    _assert_source_entries(result.choices, expected)
    _assert_no_foreign_words(result.choices, expected)


@pytest.mark.parametrize("count", (3, 4, 5))
def test_no_label_all_rewritten_neighbours_own_whole_sentences(count):
    result = _convert(" ".join(_SENTENCES[:count]), choices=_REWRITES[:count])
    expected = _SENTENCES[:count]
    _assert_source_entries(result.choices, expected)
    _assert_no_foreign_words(result.choices, expected)


def test_no_label_rewrites_without_their_first_word_still_own_whole_sentences():
    # A suffix interval of the sentence is not better evidence than the whole
    # sentence; the earliest-start tie must keep the sentence's opening words.
    result = _convert(
        " ".join(_SENTENCES[:3]),
        choices=(
            "Clarify the important concept.",
            "Clarify the crucial idea.",
            "Simplify the central theme.",
        ),
    )
    _assert_source_entries(result.choices, _SENTENCES[:3])


def test_no_label_rewrite_keeps_its_sentence_over_a_shared_boundary_word():
    source = "Explain the important context. Context is the crucial key."
    result = _convert(
        source,
        choices=("Explain the vital context.", "Context is the essential key."),
    )
    expected = ("Explain the important context.", "Context is the crucial key.")
    _assert_source_entries(result.choices, expected)
    _assert_no_foreign_words(result.choices, expected)


def test_repeated_whole_phrase_gives_each_choice_one_phrase():
    result = _convert("warm water warm water", choices=("warm water", "warm water"))
    _assert_source_entries(result.choices, ("warm water", "warm water"))


def test_repeated_whole_phrase_is_shared_across_matching_surfaces():
    source = " ".join(["warm water"] * 4)
    result = _convert(
        source,
        left=("warm water", "warm water"),
        right=("warm water", "warm water"),
    )
    _assert_source_entries(result.match_left, ("warm water", "warm water"))
    _assert_source_entries(result.match_right, ("warm water", "warm water"))


def test_quoted_ordinal_literal_is_not_an_entry_label():
    # ``A.`` is preceded by whitespace inside the quote, so the label tokenizer
    # can see it; it is quoted content, never a source entry boundary.
    source = 'Explain "why A. is a literal" in context. Describe the crucial idea.'
    result = _convert(
        source,
        choices=('Clarify "why A. is a literal" in context.', "Outline the crucial idea."),
    )
    expected = ('Explain "why A. is a literal" in context.', "Describe the crucial idea.")
    _assert_source_entries(result.choices, expected)
    _assert_no_foreign_words(result.choices, expected)


def test_rewritten_entry_keeps_its_quoted_object_and_quotes():
    source = 'Say "warm water" aloud. Use cold water.'
    result = _convert(source, choices=('Announce "warm water" aloud.', "Use cold water."))
    _assert_source_entries(result.choices, ('Say "warm water" aloud.', "Use cold water."))


def test_exact_anchor_inside_a_quote_owns_its_whole_sentence():
    source = 'Say "blue" aloud. Follow the safety note.'
    result = _convert(source, choices=("blue", "Follow the safety note."))
    _assert_source_entries(result.choices, ('Say "blue" aloud.', "Follow the safety note."))


def test_model_wording_without_quotes_still_owns_the_quoted_source():
    source = 'Identify "the important concept" clearly. Explain the crucial idea.'
    result = _convert(
        source,
        choices=("Identify the important concept clearly.", "Explain the crucial idea."),
    )
    _assert_source_entries(
        result.choices,
        ('Identify "the important concept" clearly.', "Explain the crucial idea."),
    )


def test_mixed_marks_split_each_owned_sentence_at_its_run_boundaries():
    result = _convert_runs(
        (
            ("Identify the ", ("bold",)),
            ("important concept.", ("italic",)),
            (" Explain the ", ("bold",)),
            ("crucial idea.", ("underline",)),
        ),
        choices=("Identify the vital concept.", "Explain the crucial idea."),
    )
    assert _bodies(result.choices) == [
        "Identify the important concept.",
        "Explain the crucial idea.",
    ]
    assert _segments(result.choices) == [
        [("Identify the ", ("bold",)), ("important concept.", ("italic",))],
        [("Explain the ", ("bold",)), ("crucial idea.", ("underline",))],
    ]


def test_unmarked_separator_between_mark_runs_leaves_no_mark_evidence():
    result = _convert_runs(
        (
            ("Identify the important concept.", ("bold",)),
            (" ", ()),
            ("Explain the crucial idea.", ("italic",)),
        ),
        choices=("Identify the vital concept.", "Explain the crucial idea."),
    )
    assert _bodies(result.choices) == [
        "Identify the important concept.",
        "Explain the crucial idea.",
    ]
    assert _segments(result.choices) == [
        [("Identify the important concept.", ("bold",))],
        [("Explain the crucial idea.", ("italic",))],
    ]


def test_labelled_entry_drops_its_unmarked_label_and_keeps_its_marked_wording():
    result = _convert_runs(
        (
            ("A. ", ()),
            ("Identify the important concept.", ("bold",)),
            (" B. ", ()),
            ("Explain the crucial idea.", ("italic",)),
        ),
        choices=("Identify the vital concept.", "Explain the crucial idea."),
    )
    assert _bodies(result.choices) == [
        "Identify the important concept.",
        "Explain the crucial idea.",
    ]
    assert _segments(result.choices) == [
        [("Identify the important concept.", ("bold",))],
        [("Explain the crucial idea.", ("italic",))],
    ]


_LABEL_PAIRS = (
    ("A. ", "B. "),
    ("a) ", "b) "),
    ("1. ", "2. "),
    ("I. ", "II. "),
    ("i) ", "ii) "),
    ("(1) ", "(2) "),
)


@pytest.mark.parametrize("labels", _LABEL_PAIRS)
@pytest.mark.parametrize("first_exact", (False, True))
def test_labelled_ordinal_families_keep_mixed_exact_and_rewritten_choices(labels, first_exact):
    source = f"{labels[0]}{_SENTENCES[0]} {labels[1]}{_SENTENCES[1]}"
    choices = (
        _SENTENCES[0] if first_exact else _REWRITES[0],
        _REWRITES[1] if first_exact else _SENTENCES[1],
    )
    result = _convert(source, choices=choices)
    _assert_source_entries(result.choices, _SENTENCES[:2])


_MATCH_LABELS = (
    ("1. ", "a) ", "2. ", "b) "),
    ("I. ", "i) ", "II. ", "ii) "),
    ("(1) ", "(a) ", "(2) ", "(b) "),
)
_MATCH_CASES = (
    (("red", "blue"), ("tepid", "freezing")),
    (("reddish", "bluish"), ("warm", "cold")),
    (("red", "bluish"), ("tepid", "cold")),
    (("reddish", "blue"), ("warm", "freezing")),
)


@pytest.mark.parametrize("labels", _MATCH_LABELS)
@pytest.mark.parametrize("left,right", _MATCH_CASES)
def test_labelled_matching_families_keep_mixed_exact_and_rewritten_entries(labels, left, right):
    first, second, third, fourth = labels
    source = f"{first}red {second}warm {third}blue {fourth}cold"
    result = _convert(source, left=left, right=right)
    # F3 keeps model insertions when every marked source character survives.
    # 'reddish' contains all of 'red'; 'bluish' does not contain the source 'e'.
    assert _bodies(result.match_left) == ["reddish" if left[0] == "reddish" else "red", "blue"]
    assert _segments(result.match_left) == [
        [("red", _BOLD), ("dish", ())] if left[0] == "reddish" else [("red", _BOLD)],
        [("blue", _BOLD)],
    ]
    _assert_source_entries(result.match_right, ("warm", "cold"))
