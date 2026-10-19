"""Duplicate exam titles on guest-draft handoff get a numbered title."""

from skriptoteket.domain.curated_apps.exam_workspace.exam_title_numbering import (
    numbered_exam_title,
)


def test_untaken_title_is_unchanged() -> None:
    assert numbered_exam_title("Prov", set()) == "Prov"


def test_taken_base_gets_suffix_two() -> None:
    assert numbered_exam_title("Prov", {"Prov"}) == "Prov (2)"


def test_existing_suffix_two_gives_suffix_three() -> None:
    assert numbered_exam_title("Prov", {"Prov", "Prov (2)"}) == "Prov (3)"


def test_draft_title_ending_in_suffix_counts_from_its_base() -> None:
    assert numbered_exam_title("Prov (2)", {"Prov (2)"}) == "Prov (3)"
    assert numbered_exam_title("Prov (2)", {"Prov", "Prov (2)"}) == "Prov (3)"


def test_gap_fills_lowest_free_suffix() -> None:
    assert numbered_exam_title("Prov", {"Prov", "Prov (3)"}) == "Prov (2)"


def test_unrelated_titles_do_not_force_numbering() -> None:
    assert numbered_exam_title("Prov", {"Provtagning", "Annat"}) == "Prov"


def test_base_containing_parens_percent_and_underscore() -> None:
    assert numbered_exam_title("Prov (50%)_x", set()) == "Prov (50%)_x"
    assert numbered_exam_title("Prov (50%)_x", {"Prov (50%)_x"}) == "Prov (50%)_x (2)"
    assert (
        numbered_exam_title("100%_säkert (a_b)", {"100%_säkert (a_b)"}) == "100%_säkert (a_b) (2)"
    )


def test_non_positive_suffix_is_not_a_numbered_base() -> None:
    assert numbered_exam_title("Prov (0)", {"Prov (0)"}) == "Prov (0) (2)"
    assert numbered_exam_title("Prov (x)", {"Prov (x)"}) == "Prov (x) (2)"
