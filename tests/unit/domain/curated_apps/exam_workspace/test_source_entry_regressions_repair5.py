"""Fourth-rereview ownership probes, retained as behavioral regressions."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.domain.curated_apps.exam_workspace.test_source_entry_partition_repair3 import (
    _convert,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "wordings",
    [
        ("The important concept.", "The crucial idea."),
        ("important concept.", "crucial idea."),
    ],
)
def test_short_rewrites_restore_each_omitted_opening_verb_to_its_owner(wordings):
    result = _convert(
        "Identify the important concept. Explain the crucial idea.",
        choices=wordings,
    )
    assert [body_plain_text(c.body) for c in result.choices] == [
        "Identify the important concept.",
        "Explain the crucial idea.",
    ]


def test_guillemet_ordinal_is_content_not_a_structural_slot():
    result = _convert(
        "Explain «why A. is a literal» in context. Describe the crucial idea.",
        choices=("Clarify «why A. is a literal» in context.", "Outline the crucial idea."),
    )
    assert [body_plain_text(c.body) for c in result.choices] == [
        "Explain «why A. is a literal» in context.",
        "Describe the crucial idea.",
    ]


def test_multiline_anchor_and_inline_neighbour_never_overlap():
    result = _convert(
        "First line\nContinuation first. Second idea.",
        choices=("First line Continuation first.", "Second idea."),
    )
    assert [body_plain_text(c.body) for c in result.choices] == [
        "First line\nContinuation first.",
        "Second idea.",
    ]


@pytest.mark.parametrize("count", [8, 16, 24, 32, 40])
def test_interleaved_unique_anchor_preserves_every_exact_matching_entry(count):
    result = _convert(
        "same unique " + " ".join(["same"] * (2 * count - 2)),
        left=["same"] * count,
        right=["same", "unique", *(["same"] * (count - 2))],
    )
    assert [body_plain_text(e.body) for e in result.match_left] == ["same"] * count
    assert [body_plain_text(e.body) for e in result.match_right] == [
        "same",
        "unique",
        *(["same"] * (count - 2)),
    ]
