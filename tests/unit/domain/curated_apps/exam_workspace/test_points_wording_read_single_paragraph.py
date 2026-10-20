"""A read heading consumed by the points reader leaves a sole plain paragraph.

D12 read-label correction: when ``read_heading_points`` holds the reader's
number, the first-paragraph cut runs with that number before the end-of-body
path, and a one-paragraph body is allowed when the cut paragraph keeps text
of its own. A body left with no text stays unchanged (D6). Without a reader
number behaviour is unchanged.
"""

from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    with_settled_points_wording,
)
from tests.unit.domain.curated_apps.exam_workspace.points_wording_test_support import (
    item,
    paragraph,
    text_segment,
)


def test_a_read_number_cuts_a_sole_plain_paragraph_first() -> None:
    body = (paragraph(text_segment("Förklara tempus (3 p)")),)

    result = with_settled_points_wording(item(body, 4), read_heading_points=3)

    assert result.body == (paragraph(text_segment("Förklara tempus")),)
    assert result.points == 4
    assert result.leftover_points_text is None


def test_a_read_number_keeps_the_word_of_a_sole_one_word_line() -> None:
    body = (paragraph(text_segment("Tempus 3 poäng")),)

    result = with_settled_points_wording(item(body, 4), read_heading_points=3)

    assert result.body == (paragraph(text_segment("Tempus")),)
    assert result.points == 4
    assert result.leftover_points_text is None


def test_a_read_number_leaves_a_sole_label_line_whole() -> None:
    # D6: a body of only the label keeps its paragraphs and records nothing.
    body = (paragraph(text_segment("(3 p)")),)

    result = with_settled_points_wording(item(body, 4), read_heading_points=3)

    assert result.body == body
    assert result.points == 4
    assert result.leftover_points_text is None


def test_an_absent_read_number_keeps_today_s_differing_label_rule() -> None:
    # D7: the end-of-body path compares with the settled points and records
    # the differing wording.
    body = (paragraph(text_segment("Förklara tempus (3 p)")),)

    result = with_settled_points_wording(item(body, 4), read_heading_points=None)

    assert result.body == body
    assert result.points == 4
    assert result.leftover_points_text == "(3 p)"
