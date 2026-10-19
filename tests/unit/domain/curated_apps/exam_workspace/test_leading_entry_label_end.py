"""The leading ordinal list label of a paragraph (TASK-SKRIPT-39-04-18).

Structural only: the label is an ordinal token from any ordinal family with its
delimiter at the paragraph start, exactly as ``entry_label_end`` recognizes it.
Never wording.
"""

import pytest

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
