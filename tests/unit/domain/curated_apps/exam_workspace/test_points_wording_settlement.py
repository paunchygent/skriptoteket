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
    _heading,
    _item,
    _paragraph,
    _text,
)


def test_differing_number_keeps_text_and_review_even_when_run_twice() -> None:
    item = _item((_paragraph(_text("Fråga. (3 p)")),), 2)
    result = with_settled_points_wording(item)
    assert result.body == item.body
    assert result.points == item.points
    assert result.review == item.review
    assert result.leftover_points_text == "(3 p)"
    second = with_settled_points_wording(result)
    assert second.body == item.body
    assert second.points == item.points
    assert second.review == item.review
    assert second.leftover_points_text == "(3 p)"


def test_missing_points_keeps_text_and_review() -> None:
    item = _item((_paragraph(_text("Fråga. (3 p)")),), None)
    assert with_settled_points_wording(item) == item


def test_nothing_is_recorded_without_points() -> None:
    body = (_paragraph(_text("Fråga. (3 p)")),)
    assert leftover_points_wording(body, None) is None
    assert with_settled_points_wording(_item(body, None)).leftover_points_text is None


def test_settled_item_is_idempotent_and_keeps_points_and_review() -> None:
    body = (_paragraph(_text("Svara utförligt och tydligt. (3 p)")),)
    item = _item(body, 2)
    once = with_settled_points_wording(item)
    assert once.leftover_points_text == "(3 p)"
    assert once.points == 2
    assert once.review == item.review
    assert with_settled_points_wording(once) == once


def test_first_paragraph_points_only_line_with_label_at_each_end_stays() -> None:
    # D3: several labels leave everything untouched.
    body = (
        _paragraph(_text("Poäng: 2 poäng")),
        _paragraph(_text("Svara. (2 p)")),
    )
    result = with_settled_points_wording(_item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None


def test_settled_item_with_two_labels_on_one_line_keeps_everything() -> None:
    for text in ("Räkna. (1 p) (2 p)", "Räkna. (2 p) (2 p)"):
        body = (_paragraph(_text(text)),)
        item = with_settled_points_wording(_item(body, 2))
        assert item.body == body
        assert item.leftover_points_text is None


def test_settled_item_with_two_points_lines_keeps_everything_and_is_idempotent() -> None:
    body = (
        _paragraph(_text("Fråga.")),
        _paragraph(_text("Poäng: 2 poäng")),
        _paragraph(_text("Poäng: 2 poäng")),
    )
    once = with_settled_points_wording(_item(body, 2))
    assert once.body == body
    assert once.leftover_points_text is None
    assert with_settled_points_wording(once) == once


def test_settled_item_with_a_label_at_each_end_keeps_everything() -> None:
    body = (
        _paragraph(_text("Fråga. (2 p)")),
        _paragraph(_text("Avslutning. (3 p)")),
    )
    item = with_settled_points_wording(_item(body, 2))
    assert item.body == body
    assert item.leftover_points_text is None


def test_matching_labels_at_both_ends_leave_and_settling_is_idempotent() -> None:
    # D3 (with several labels nothing is removed) and review F3: an item
    # whose body holds more than one points label keeps both labels.
    body = (
        _paragraph(_text("Frågan inleds här. (2 p)")),
        _paragraph(_text("Frågan avslutas här. (2 p)")),
    )
    once = with_settled_points_wording(_item(body, 2))
    assert once.body == body
    assert once.leftover_points_text is None
    assert with_settled_points_wording(once) == once


def test_mid_body_heading_plus_end_label_abstains() -> None:
    # D3: two labels abstain; nothing is removed and nothing is recorded.
    body = (
        _paragraph(_text("Läs texterna.")),
        _paragraph(_text("Text A")),
        _paragraph(_text('"Igår kom jag."')),
        _paragraph(_text("Text B")),
        _paragraph(_text('"Ett haveri."')),
        _heading("Jämför texterna (15 p)"),
        _paragraph(_text("Beskriv minst fyra skillnader.")),
        _paragraph(_text("Svara. (15 p)")),
    )
    result = with_settled_points_wording(_item(body, 15))
    assert result.body == body
    assert result.leftover_points_text is None


def test_heading_bare_label_plus_end_label_abstains() -> None:
    # D3: two labels abstain; nothing is removed and nothing is recorded.
    body = (
        _heading("Uppgift 3 – 4 poäng"),
        _paragraph(_text("Svara. (4 p)")),
    )
    result = with_settled_points_wording(_item(body, 4))
    assert result.body == body
    assert result.leftover_points_text is None
