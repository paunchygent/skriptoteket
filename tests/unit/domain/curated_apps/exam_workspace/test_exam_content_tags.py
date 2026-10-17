"""Central-content identities and threshold citations are source-bound."""

import pytest

from scripts.build_exam_course_catalog import split_content_items
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    ExamContentItem,
    aggregate_content_tags,
    content_item_id,
)


def test_bullets_preserve_nested_inline_text_and_entities_not_headings() -> None:
    items = split_content_items(
        "SVESVE02",
        "<h4>Innehåll</h4><ul><li>Språk <em>och</em> stil &amp; form.</li>"
        "<li>Textanalys.<br>Jämförelser.</li></ul>",
    )
    assert [item.text for item in items] == ["Språk och stil & form.", "Textanalys. Jämförelser."]
    assert items[0].id == "SVESVE02:språk och stil & form."
    assert content_item_id("SVESVE02", "  SPRÅK  och stil & form. ") == items[0].id
    assert content_item_id("SVESVE03", items[0].text) != items[0].id


def test_threshold_inclusive_citations_stay_per_winning_question() -> None:
    items = (ExamContentItem(id="s:a", text="A"), ExamContentItem(id="s:b", text="B"))
    tags = aggregate_content_tags(
        items,
        [
            ("q1", "s:a", 0.9),
            ("q2", "s:a", 0.99),
            ("q3", "s:b", 0.899999),
            ("q4", None, 1.0),
            ("q5", "other", 1.0),
        ],
    )
    assert len(tags) == 1
    assert tags[0].id == "s:a"
    assert tags[0].origin == "suggested"
    assert tags[0].question_ids == ("q1", "q2")


@pytest.mark.parametrize("html", ["<p>No bullets</p>", "<ul><li></li></ul>", "<li>Unclosed"])
def test_absent_or_incomplete_bullets_cannot_be_guessed(html: str) -> None:
    with pytest.raises(ValueError):
        split_content_items("SVESVE02", html)
