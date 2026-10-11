"""Points lines judged against real corpus chunks."""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import points_line
from tests.unit.domain.curated_apps.exam_workspace.source_rules_test_support import (
    chunks_by_anchor,
)


@pytest.mark.parametrize(
    ("docx", "anchor"),
    [
        ("svenska_2_grammatik_omprov_variant_1_med_facit", "body:0004"),
        ("svenska_2_grammatik_omprov_variant_1_med_facit", "body:0013"),
        ("bf26_diagnostic_grammar_test_ht26_med_facit", "body:0003"),
        ("bf26_english_1_unit_test_kap_1_2_med_facit", "body:0003"),
    ],
)
def test_total_and_points_lines_are_points_lines(docx: str, anchor: str):
    text = chunks_by_anchor(docx)[anchor].text
    assert text.startswith(("Total:", "Poäng:"))
    assert points_line(text)


@pytest.mark.parametrize(
    ("docx", "anchor"),
    [
        ("bf26_english_1_unit_test_kap_1_2_med_facit", "body:0058"),
        ("chapter_4_poetry_and_lyrics_quiz_med_facit", "body:0129"),
    ],
)
def test_sentence_or_heading_that_mentions_points_is_not_a_points_line(docx: str, anchor: str):
    text = chunks_by_anchor(docx)[anchor].text
    assert "point" in text
    assert not points_line(text)
