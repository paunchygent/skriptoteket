"""The leading ordinal list label of a paragraph (TASK-SKRIPT-39-04-18).

Structural only: the label is an ordinal token from any ordinal family with its
delimiter at the paragraph start, exactly as ``entry_label_end`` recognizes it.
Never wording.
"""

import pytest

import skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage as coverage
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    leading_entry_label_end,
)

pytestmark = pytest.mark.unit


def test_a_lower_list_label_ends_after_its_delimiter_and_space():
    assert leading_entry_label_end("a) snöbollarnas Svar: x") == 3


def test_a_bare_word_is_no_label_even_with_a_colon():
    assert leading_entry_label_end("Svar: x") is None


def test_a_single_paragraph_label_needs_no_body_length_bound():
    assert leading_entry_label_end("c) ord") == 3


def test_a_roman_token_without_a_delimiter_is_no_label():
    assert leading_entry_label_end("I think") is None


def test_a_parenthesized_roman_label_ends_after_its_closer_and_space():
    assert leading_entry_label_end("(iv) ord") == 5


def test_a_dotted_decimal_label_ends_after_its_delimiter_and_space():
    assert leading_entry_label_end("2. ord") == 3


def test_unlabelled_text_builds_no_ordinal_token(monkeypatch):
    """Unlabelled text returns None without ever inferring an ordinal (F1).

    The delimiter structure comes first: a space after the leading token is
    no delimiter, and an opener without its closer is no label either. No
    ordinal is computed for such text, so no cross-family numeral expansion
    can follow. The spy fails fast on the old code instead of hanging.
    """

    def _forbidden(family: str, ordinal: int) -> str | None:
        raise AssertionError(f"_ordinal_token called for unlabelled text: {family} {ordinal}")

    monkeypatch.setattr(coverage, "_ordinal_token", _forbidden)
    for text in (
        "question text Svar: x",
        "QUESTION text Svar: x",
        "a text",
        "12 text",
        "(a. text",
        "(question text",
    ):
        assert leading_entry_label_end(text) is None


def _candidate_families(token: str) -> set[str]:
    families: set[str] = set()
    if token.isdigit():
        families.add("decimal")
    elif token.isalpha():
        if token.isupper():
            families.add("upper")
        if token.islower():
            families.add("lower")
        if coverage._roman_value(token) is not None:
            if token.isupper():
                families.add("roman_upper")
            if token.islower():
                families.add("roman_lower")
    return families


@pytest.mark.parametrize(
    ("text", "token", "expected_end"),
    [("question) text", "question", 10), ("QUESTION. text", "QUESTION", 10)],
)
def test_labelled_long_tokens_only_build_candidate_family_tokens(
    monkeypatch, text: str, token: str, expected_end: int
):
    """Labelled long tokens only build tokens of their own families (F1).

    Every recorded ``_ordinal_token`` call stays in the token's own candidate
    families, and roman calls stay linear in the token length. The answer
    equals the delimiter end. The guard fails fast on the old code, where the
    inferred ordinal reaches every family, instead of hanging in roman ``M``.
    """
    real_ordinal_token = coverage._ordinal_token
    calls: list[tuple[str, int]] = []

    def _recording(family: str, ordinal: int) -> str | None:
        calls.append((family, ordinal))
        assert family in _candidate_families(token), (
            f"non-candidate family built for {token!r}: {family} {ordinal}"
        )
        if family.startswith("roman"):
            assert ordinal <= 1000 * len(token), (
                f"unbounded roman ordinal for {token!r}: {family} {ordinal}"
            )
        return real_ordinal_token(family, ordinal)

    monkeypatch.setattr(coverage, "_ordinal_token", _recording)

    assert leading_entry_label_end(text) == expected_end
    assert calls, f"expected candidate round trips for {token!r}"


def test_a_long_decimal_label_needs_no_int_conversion():
    assert leading_entry_label_end("1" * 5000 + ". Svar: x") == 5002


def test_a_zero_decimal_token_is_no_label():
    assert leading_entry_label_end("0. x") is None


def test_a_zero_padded_decimal_token_is_no_label():
    assert leading_entry_label_end("01. x") is None


def test_a_parenthesized_decimal_label_ends_after_its_closer_and_space():
    assert leading_entry_label_end("10) x") == 4
