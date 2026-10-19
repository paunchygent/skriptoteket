"""Points wording in the first paragraph of an item body.

Parenthesised labels ending the first paragraph, first paragraphs that hold
only points wording (D12 decision E), and one-word heads keeping their word
in the first paragraph (D12 Correction).
"""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeGapSegment
from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    with_settled_points_wording,
)
from tests.unit.domain.curated_apps.exam_workspace.points_wording_test_support import (
    VOLT,
    heading,
    item,
    paragraph,
    text_segment,
)


def test_first_paragraph_heading_label_leaves_and_keeps_its_level() -> None:
    body = (
        heading("5. Resor till skolan (1 poäng)"),
        paragraph(text_segment("En grupp skriver om hur elever tar sig till skolan.")),
    )
    result = with_settled_points_wording(item(body, 1))
    assert result.body[0].heading_level == 3
    assert result.body[0] == heading("5. Resor till skolan")
    assert result.body[1:] == body[1:]
    assert result.points == 1
    assert result.leftover_points_text is None


def test_first_paragraph_non_heading_label_leaves() -> None:
    body = (
        paragraph(text_segment("1. Select the word or phrase for each definition. (3 points)")),
        paragraph(text_segment("Write the letter of the matching option.")),
        paragraph(text_segment("1. absence from school | ____ | A. truancy")),
    )
    result = with_settled_points_wording(item(body, 3))
    assert result.body[0] == paragraph(
        text_segment("1. Select the word or phrase for each definition.")
    )
    assert result.body[1:] == body[1:]
    assert result.leftover_points_text is None


def test_first_paragraph_multiline_label_leaves_the_text_before_it() -> None:
    first = (
        "1. Milan tends to boast when he meets new teammates.\n\n"
        "What does boast mean here? (1 point)"
    )
    body = (paragraph(text_segment(first)), paragraph(text_segment("A. skryta")))
    result = with_settled_points_wording(item(body, 1))
    assert result.body[0] == paragraph(
        text_segment(
            "1. Milan tends to boast when he meets new teammates.\n\nWhat does boast mean here?"
        )
    )
    assert result.body[1:] == body[1:]


def test_first_paragraph_differing_number_stays_and_records_nothing() -> None:
    body = (
        paragraph(text_segment("2. Tidningsartiklar (2 poäng)")),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 3))
    assert result.body == body
    assert result.points == 3
    assert result.leftover_points_text is None


def test_first_paragraph_label_without_points_is_untouched() -> None:
    body = (
        paragraph(text_segment("2. Tidningsartiklar (2 poäng)")),
        paragraph(text_segment("Svara utförligt.")),
    )
    assert with_settled_points_wording(item(body, None)) == item(body, None)


def test_first_paragraph_in_sentence_label_is_untouched() -> None:
    body = (
        paragraph(text_segment("Svara (2 p) och motivera.")),
        paragraph(text_segment("Fortsätt här.")),
    )
    assert with_settled_points_wording(item(body, 2)) == item(body, 2)


def test_first_paragraph_one_word_head_parenthesised_label_leaves_only_the_label() -> None:
    # D12: the label leaves, never the line; its number must equal the points (D3).
    body = (
        paragraph(text_segment("Tidningsartiklar (2 poäng)")),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 2))
    assert result.body == (
        paragraph(text_segment("Tidningsartiklar")),
        paragraph(text_segment("Svara utförligt.")),
    )
    assert result.leftover_points_text is None


def test_first_paragraph_one_word_head_label_with_other_points_stays() -> None:
    body = (
        paragraph(text_segment("Tidningsartiklar (2 poäng)")),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 3))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_bare_label_paragraph_is_dropped_when_other_text_remains() -> None:
    # D12, D6: a first paragraph emptied by the cut is dropped while the body keeps other text.
    body = (paragraph(text_segment("(2 p)")), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 2))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_first_paragraph_bare_label_paragraph_with_other_points_stays() -> None:
    body = (paragraph(text_segment("(2 p)")), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 3))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_points_only_line_leaves_at_equal_points() -> None:
    # D12 decision E: a first paragraph that is a points-only line leaves whole at equal points.
    body = (paragraph(text_segment("Poäng: 2 poäng")), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 2))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_first_paragraph_points_only_line_with_other_points_stays() -> None:
    # D12 decision E: a differing number stays and is not recorded.
    body = (
        paragraph(text_segment("Poäng: 2 poäng")),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 3))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_totalt_points_only_line_leaves_at_equal_points() -> None:
    # D12 decision E: any head a points-only line accepts counts.
    body = (paragraph(text_segment("Totalt: 36 p")), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 36))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_first_paragraph_max_points_only_line_leaves_at_equal_points() -> None:
    # D12 fourth extension: a one-word head without a colon keeps its word;
    # only the label leaves.
    body = (paragraph(text_segment("Max 36p")), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 36))
    assert result.body == (
        paragraph(text_segment("Max")),
        paragraph(text_segment("Svara utförligt.")),
    )
    assert result.leftover_points_text is None


def test_first_paragraph_topic_word_head_keeps_its_word() -> None:
    # D12 fourth extension: a one-word head without a colon keeps its word;
    # only the label leaves.
    body = (
        paragraph(text_segment("Tempus 3 poäng")),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 3))
    assert result.body == (
        paragraph(text_segment("Tempus")),
        paragraph(text_segment("Svara utförligt.")),
    )
    assert result.leftover_points_text is None


def test_first_paragraph_points_only_line_alone_stays() -> None:
    # D12 decision E, D6: a body of only that paragraph stays.
    body = (paragraph(text_segment("Poäng: 2 poäng")),)
    result = with_settled_points_wording(item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_prose_after_label_stays() -> None:
    # D12 decision E: prose after the label is never a points-only line.
    body = (
        paragraph(text_segment("Poäng: 2 poäng är max")),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_ending_in_a_gap_is_untouched() -> None:
    body = (
        paragraph(text_segment("Svara (2 p)"), NativeGapSegment(gap_id="gap_001")),
        paragraph(text_segment("Fortsätt här.")),
    )
    assert with_settled_points_wording(item(body, 2)) == item(body, 2)


def test_first_paragraph_volt_question_is_untouched() -> None:
    body = (paragraph(text_segment(VOLT)), paragraph(text_segment("Fortsätt här.")))
    result = with_settled_points_wording(item(body, 5))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_bare_only_label_is_dropped_when_other_text_remains() -> None:
    # D12 extension E: heading_level comes from the Word heading style, so a
    # heading chunk without a style level reaches the final gate as a plain
    # first paragraph that is only its points wording.
    body = (paragraph(text_segment("1 point")), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 1))
    assert result.body == (paragraph(text_segment("Svara utförligt.")),)
    assert result.leftover_points_text is None


def test_first_paragraph_bare_only_label_with_other_points_stays() -> None:
    body = (paragraph(text_segment("1 point")), paragraph(text_segment("Svara utförligt.")))
    result = with_settled_points_wording(item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_bare_label_with_other_words_stays() -> None:
    body = (
        paragraph(text_segment("Uppgift 3 – 4 poäng")),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 4))
    assert result.body == body
    assert result.leftover_points_text is None


def test_first_paragraph_trailing_bare_label_in_a_sentence_stays() -> None:
    body = (
        paragraph(text_segment("Beskriv fotosyntesen, 2 p")),
        paragraph(text_segment("Svara utförligt.")),
    )
    result = with_settled_points_wording(item(body, 2))
    assert result.body == body
    assert result.leftover_points_text is None
