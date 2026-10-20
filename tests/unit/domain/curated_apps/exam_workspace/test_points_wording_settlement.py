"""Settlement of points wording on the final item.

The final gate settles the end, first-paragraph and heading outcomes against
the item's points; several labels abstain (D3) and nothing is recorded
without settled points.
"""

from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    leftover_points_wording,
    with_settled_points_wording,
)
from tests.unit.domain.curated_apps.exam_workspace.points_wording_test_support import (
    heading,
    item,
    paragraph,
    text_segment,
)


def test_differing_number_keeps_text_and_review_even_when_run_twice() -> None:
    exam_item = item((paragraph(text_segment("Fråga. (3 p)")),), 2)
    result = with_settled_points_wording(exam_item, read_heading_points=None)
    assert result.body == exam_item.body
    assert result.points == exam_item.points
    assert result.review == exam_item.review
    assert result.leftover_points_text == "(3 p)"
    second = with_settled_points_wording(result, read_heading_points=None)
    assert second.body == exam_item.body
    assert second.points == exam_item.points
    assert second.review == exam_item.review
    assert second.leftover_points_text == "(3 p)"


def test_missing_points_keeps_text_and_review() -> None:
    exam_item = item((paragraph(text_segment("Fråga. (3 p)")),), None)
    assert with_settled_points_wording(exam_item, read_heading_points=None) == exam_item


def test_nothing_is_recorded_without_points() -> None:
    body = (paragraph(text_segment("Fråga. (3 p)")),)
    assert leftover_points_wording(body, None) is None
    result = with_settled_points_wording(item(body, None), read_heading_points=None)
    assert result.leftover_points_text is None


def test_settled_item_is_idempotent_and_keeps_points_and_review() -> None:
    body = (paragraph(text_segment("Svara utförligt och tydligt. (3 p)")),)
    exam_item = item(body, 2)
    once = with_settled_points_wording(exam_item, read_heading_points=None)
    assert once.leftover_points_text == "(3 p)"
    assert once.points == 2
    assert once.review == exam_item.review
    assert with_settled_points_wording(once, read_heading_points=None) == once


def test_first_paragraph_points_only_line_with_label_at_each_end_stays() -> None:
    # D3: several labels leave everything untouched.
    body = (
        paragraph(text_segment("Poäng: 2 poäng")),
        paragraph(text_segment("Svara. (2 p)")),
    )
    result = with_settled_points_wording(item(body, 2), read_heading_points=None)
    assert result.body == body
    assert result.leftover_points_text is None


def test_settled_item_with_two_labels_on_one_line_keeps_everything() -> None:
    for text in ("Räkna. (1 p) (2 p)", "Räkna. (2 p) (2 p)"):
        body = (paragraph(text_segment(text)),)
        exam_item = with_settled_points_wording(item(body, 2), read_heading_points=None)
        assert exam_item.body == body
        assert exam_item.leftover_points_text is None


def test_settled_item_with_two_points_lines_keeps_everything_and_is_idempotent() -> None:
    body = (
        paragraph(text_segment("Fråga.")),
        paragraph(text_segment("Poäng: 2 poäng")),
        paragraph(text_segment("Poäng: 2 poäng")),
    )
    once = with_settled_points_wording(item(body, 2), read_heading_points=None)
    assert once.body == body
    assert once.leftover_points_text is None
    assert with_settled_points_wording(once, read_heading_points=None) == once


def test_settled_item_with_a_label_at_each_end_keeps_everything() -> None:
    body = (
        paragraph(text_segment("Fråga. (2 p)")),
        paragraph(text_segment("Avslutning. (3 p)")),
    )
    exam_item = with_settled_points_wording(item(body, 2), read_heading_points=None)
    assert exam_item.body == body
    assert exam_item.leftover_points_text is None


def test_matching_labels_at_both_ends_leave_and_settling_is_idempotent() -> None:
    # D3 (with several labels nothing is removed) and review F3: an item
    # whose body holds more than one points label keeps both labels.
    body = (
        paragraph(text_segment("Frågan inleds här. (2 p)")),
        paragraph(text_segment("Frågan avslutas här. (2 p)")),
    )
    once = with_settled_points_wording(item(body, 2), read_heading_points=None)
    assert once.body == body
    assert once.leftover_points_text is None
    assert with_settled_points_wording(once, read_heading_points=None) == once


def test_mid_body_heading_plus_end_label_abstains() -> None:
    # D3: two labels abstain; nothing is removed and nothing is recorded.
    body = (
        paragraph(text_segment("Läs texterna.")),
        paragraph(text_segment("Text A")),
        paragraph(text_segment('"Igår kom jag."')),
        paragraph(text_segment("Text B")),
        paragraph(text_segment('"Ett haveri."')),
        heading("Jämför texterna (15 p)"),
        paragraph(text_segment("Beskriv minst fyra skillnader.")),
        paragraph(text_segment("Svara. (15 p)")),
    )
    result = with_settled_points_wording(item(body, 15), read_heading_points=None)
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_bare_label_plus_end_label_abstains() -> None:
    # D3: two labels abstain; nothing is removed and nothing is recorded.
    body = (
        heading("Uppgift 3 – 4 poäng"),
        paragraph(text_segment("Svara. (4 p)")),
    )
    result = with_settled_points_wording(item(body, 4), read_heading_points=None)
    assert result.body == body
    assert result.leftover_points_text is None
