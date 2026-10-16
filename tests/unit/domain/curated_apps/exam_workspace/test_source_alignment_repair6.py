"""Token provenance, structural partitioning and recovered-metadata regressions."""

import random
from unittest.mock import patch

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_native_carriers import emitted_positions
from tests.unit.domain.curated_apps.exam_workspace.test_source_carrier_provenance_repair5 import (
    convert,
)
from tests.unit.domain.curated_apps.exam_workspace.test_source_entry_partition_repair3 import (
    _convert,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "suffix",
    [
        "plus",
        "pretty",
        "2",
        "p",
        "perhaps",
        "whatever",
        "(extra)",
        "extra.",
        "new (notes)",
        "new: answer",
        "extra 2 points",
        "red",
    ],
)
def test_score_does_not_borrow_provenance_from_model_insertions(suffix):
    result = convert("A. red B. blue (2 p)", ["red", "blue " + suffix])
    assert body_plain_text(result.choices[1].body) == "blue " + suffix


@pytest.mark.parametrize(
    "answer,insertion",
    [
        ("p", "plus"),
        ("water", "whatever"),
        ("a", "extra"),
        ("B", "BUT"),
        ("2", "2 extra"),
        ("private", "privateer"),
    ],
)
@pytest.mark.parametrize("continuation", ["", "\nFollow the safety note."])
def test_answer_tail_never_borrows_model_word_provenance(answer, insertion, continuation):
    result = convert(
        "A. red B. blue" + continuation + "\nSvar: " + answer, ["red", "blue " + insertion]
    )
    visible = body_plain_text(result.choices[1].body)
    assert "Svar:" not in visible
    if continuation:
        assert visible.strip() == "blue" + continuation
    else:
        assert visible == "blue " + insertion
    assert result.facit_text is None


@pytest.mark.parametrize(
    "prompt",
    [
        "Choose the correct option.",
        "Select the correct answer.",
        "Describe the right option.",
        "Explain why B is correct.",
    ],
)
def test_body_provenance_cannot_enter_entry_answer_regions(prompt):
    result = convert(
        "A. red B. blue\nFollow the safety note.\nSvar:\nThe correct option is B.",
        ["red", "blue"],
        prompt=prompt,
    )
    assert body_plain_text(result.choices[1].body).strip() == "blue\nFollow the safety note."


@pytest.mark.parametrize("separator", [" ", "\n", "; ", ", ", ": ", " and ", " (2 p) "])
@pytest.mark.parametrize(
    "first",
    ["The important concept.", "The important concept", "important concept.", "important concept"],
)
def test_added_punctuation_never_consumes_the_next_entries_word(separator, first):
    result = convert(
        "Identify the important concept" + separator + "Explain the crucial idea.",
        [first, "The crucial idea."],
    )
    visible = [body_plain_text(c.body).strip() for c in result.choices]
    assert "Explain" not in visible[0]
    assert visible[1] in {"Explain the crucial idea.", "and Explain the crucial idea."}
    assert "(2 p)" not in "\n".join(visible)


@pytest.mark.parametrize("first", ["The important concept.", "important concept."])
@pytest.mark.parametrize(
    "source",
    [
        ["Identify the important concept", "Explain the crucial idea."],
        "A. Identify the important concept B. Explain the crucial idea.",
        "A. red B. (2 p) Important blue",
    ],
)
def test_structural_boundaries_are_not_consumed_by_previous_entry(source, first):
    wordings = ["red", "blue"] if "Important blue" in source else [first, "The crucial idea."]
    result = convert(source, wordings)
    visible = [body_plain_text(c.body).strip() for c in result.choices]
    expected = (
        ["red", "Important blue"]
        if "Important blue" in source
        else ["Identify the important concept", "Explain the crucial idea."]
    )
    assert visible == expected


def test_separate_answer_paragraph_does_not_leak_scattered_letters():
    result = convert(["A. red B. blue", "Svar: water"], ["red", "blue whatever"])
    assert "water" not in body_plain_text(result.choices[1].body)


def test_recovered_score_can_share_a_gap_with_visible_continuation():
    result = convert("A. red B. blue (2 p) Additional warning", ["red", "blue"])
    assert body_plain_text(result.choices[1].body).strip() == "blue  Additional warning"


def test_provenance_is_contiguous_within_aligned_tokens():
    assert not emitted_positions("water", "whatever")
    assert not emitted_positions("p", "plus")
    # Mark placement may still retain red's bold inside reddish; content
    # provenance itself requires a copied token, not copied letters.
    assert not emitted_positions("red", "reddish")


def test_seeded_scattered_carriers_and_structural_boundaries():
    rng = random.Random(3909086)
    for case in range(72):
        answer, insertion = rng.choice(
            [("water", "whatever"), ("p", "plus"), ("private", "privateer")]
        )
        source = rng.choice(
            [
                "A. Identify the important concept B. blue",
                ["Identify the important concept", "blue"],
            ]
        )
        parts = [source] if isinstance(source, str) else source
        parts = [*parts[:-1], parts[-1] + "\nFollow the safety note.\nSvar: " + answer]
        result = convert(
            parts,
            [rng.choice(["important concept.", "The important concept."]), "blue " + insertion],
        )
        visible = [body_plain_text(c.body).strip() for c in result.choices]
        assert visible == ["Identify the important concept", "blue\nFollow the safety note."], (
            case,
            visible,
        )
        assert result.facit_text is None


@pytest.mark.parametrize("count", [8, 16, 24, 32, 40])
def test_recovered_scores_keep_exact_alignment_linear(count):
    import skriptoteket.domain.curated_apps.exam_workspace.source_entry_alignment as alignment

    original = alignment.heappop
    with patch.object(alignment, "heappop", wraps=original) as pops:
        result = _convert(
            " ".join(["same (2 p)"] * (2 * count)), left=["same"] * count, right=["same"] * count
        )
    assert [body_plain_text(e.body).strip() for e in result.match_left] == ["same"] * count
    assert [body_plain_text(e.body).strip() for e in result.match_right] == ["same"] * count
    assert pops.call_count < 80 * count
