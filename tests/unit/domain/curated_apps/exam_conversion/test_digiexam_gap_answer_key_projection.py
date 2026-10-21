"""Tests for gap-fill answer-key label derivation."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_prompts import (
    numbered_gap_labels,
)


@pytest.mark.parametrize(
    ("cloze_text", "gap_count", "expected"),
    [
        (
            "Kingdom of mushrooms: [1] Domain of bacteria: [2]",
            2,
            ("Kingdom of mushrooms", "Domain of bacteria"),
        ),
        ("Name: [1]\nAge: [2]", 2, ("Name", "Age")),
        ("[1] [2]", 2, ("", "")),
        ("[1]", 1, ("",)),
        ("Only one: [1]", 2, ("Only one", "")),
        ("Missing first [2]", 2, ("", "Missing first")),
        ("Ratio: [1]:[2]", 2, ("Ratio", "")),
        ("Time:: [1]", 1, ("Time:",)),
        ("Before [1] middle [2] after", 2, ("Before", "middle")),
        ("Line one\nprefix [1] and [3] then [2]", 2, ("prefix", "then")),
        ("Scores [1] and [10]", 1, ("Scores",)),
        ("", 1, ("",)),
        ("Anything [1]", 0, ()),
    ],
)
def test_numbered_gap_labels(cloze_text: str, gap_count: int, expected: tuple[str, ...]) -> None:
    assert numbered_gap_labels(cloze_text, gap_count) == expected
