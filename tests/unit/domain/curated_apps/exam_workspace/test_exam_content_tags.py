"""Central-content identities and threshold citations are source-bound."""

import pytest

from scripts.build_exam_course_catalog import split_content_items
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    ExamContentItem,
    aggregate_content_tags,
    content_item_id,
    load_exam_content_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
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


def test_committed_content_snapshot_covers_every_catalog_key_and_real_source_gaps() -> None:
    content = load_exam_content_catalog()
    assert set(content) == {course.key for course in load_exam_course_catalog().courses}
    assert content["ATVO1000X"] == ()
    assert len(content["SVESVE02"]) == 6
    assert len(content["STAS1000X"]) == 21
    assert content["GRGRSVE01/7-9"]
    for key, items in content.items():
        assert len({item.id for item in items}) == len(items)
        assert all(item.id == content_item_id(key, item.text) for item in items)


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


def test_official_content_without_bullets_is_an_explicit_empty_source_gap() -> None:
    assert (
        split_content_items(
            "ATVO1000X",
            "<p>Undervisningen på nivå 1 ska behandla följande centrala innehåll:</p>",
        )
        == ()
    )


def test_empty_bullets_add_no_tag_and_do_not_discard_real_content() -> None:
    items = split_content_items("STAS1000X", "<ul><li>Städarbete.</li><li>  </li></ul>")
    assert [item.text for item in items] == ["Städarbete."]
    assert split_content_items("STAS1000X", "<ul><li></li></ul>") == ()


@pytest.mark.parametrize("html", ["<li>Unclosed", "</li>", "<li>A<ul><li>B</li></ul></li>"])
def test_absent_or_incomplete_bullets_cannot_be_guessed(html: str) -> None:
    with pytest.raises(ValueError):
        split_content_items("SVESVE02", html)
