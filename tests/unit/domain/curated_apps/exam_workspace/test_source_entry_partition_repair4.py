"""Unlabelled source ownership uses whole tokens and one disjoint assignment."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.domain.curated_apps.exam_workspace.test_source_entry_partition_repair3 import (
    _convert,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("prefix", ["", "A. "])
def test_rewritten_neighbours_own_complete_source_sentences(prefix):
    separator = " B. " if prefix else " "
    result = _convert(
        prefix + "Identify the important concept." + separator + "Explain the crucial idea.",
        choices=("Describe the important concept.", "State the crucial idea."),
    )
    assert [body_plain_text(e.body) for e in result.choices] == [
        "Identify the important concept.",
        "Explain the crucial idea.",
    ]


def test_unlabelled_matching_rewrites_interleave_without_crossing_surface_owners():
    result = _convert(
        "Identify the red concept. Explain the warm idea. "
        "Identify the blue concept. Explain the cold idea.",
        left=("Describe the red concept.", "Describe the blue concept."),
        right=("State the warm idea.", "State the cold idea."),
    )
    assert [body_plain_text(e.body) for e in result.match_left] == [
        "Identify the red concept.",
        "Identify the blue concept.",
    ]
    assert [body_plain_text(e.body) for e in result.match_right] == [
        "Explain the warm idea.",
        "Explain the cold idea.",
    ]


def test_point_expression_variable_is_not_the_sixteenth_ordinal():
    texts = ("Calculate (2 p) times q.", *(["same"] * 15))
    result = _convert(" ".join(texts), choices=texts)
    assert [body_plain_text(e.body) for e in result.choices] == list(texts)


@pytest.mark.parametrize("count", [8, 16, 24, 32, 40])
def test_unlabelled_duplicate_exact_allocation_preserves_every_entry(count):
    result = _convert(
        " ".join(["same"] * (2 * count)), left=["same"] * count, right=["same"] * count
    )
    assert [body_plain_text(e.body) for e in (*result.match_left, *result.match_right)] == [
        "same"
    ] * (2 * count)
