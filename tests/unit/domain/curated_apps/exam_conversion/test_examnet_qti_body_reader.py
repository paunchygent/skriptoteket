"""Round-trip tests for the Exam.net QTI rich-content reader.

Purpose:
    Prove that `examnet_qti_body_reader` inverts the rich-content rendering of
    `examnet_qti_rich_text` and `examnet_qti_inline_prompt` from the parsed,
    indented XML the export writes: paragraphs, heading levels, nested marks,
    line breaks, images and gaps at their source position.

Relationships:
    - Exercises `domain.examnet_qti_body_reader` with writer-built elements
      serialized through `domain.examnet_qti_item_xml`.
    - Split from the oversized body-reader module; shared builders live in
      `examnet_qti_reader_test_support` and are imported, never copied.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_body_reader import (
    read_rich_content,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiImageResource,
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptGap,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_rich_text import (
    append_marked_text,
    paragraph_element,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    body_free_text as _free_text,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    body_gap as _gap,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    body_prompt as _prompt,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    body_roundtrip as _roundtrip,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    qti_tag as _tag,
)

pytestmark = pytest.mark.unit

_IMAGE_PATHS = ("images/q1-image_001.png", "images/q1-image_002.png")


def _root(item: ExamNetQtiItem, image_paths: tuple[str, ...] = ()) -> ElementTree.Element:
    return ElementTree.fromstring(serialize_qti_assessment_item(item, image_paths=image_paths))


def _item_body(root: ElementTree.Element) -> ElementTree.Element:
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    return body


def _image(number: int, alt: str) -> ExamNetQtiImageResource:
    return ExamNetQtiImageResource(
        asset_id=f"image_{number:03d}",
        filename=f"q1-image-{number:03d}.png",
        media_type="image/png",
        payload=b"png-bytes",
        alt_text=alt,
        source_reference=f"asset_{number}",
    )


def test_single_plain_prompt_paragraph_round_trips_directly_in_the_prompt() -> None:
    item = _free_text(
        (
            ExamNetQtiPromptParagraph(
                segments=(
                    ExamNetQtiPromptText("Före "),
                    ExamNetQtiPromptGap(0),
                    ExamNetQtiPromptText(" efter."),
                )
            ),
        ),
        text_entry_gaps=(_gap(1, ("alfa",)),),
    )

    prompt = _prompt(_root(item))

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptText("Före "),
                ExamNetQtiPromptGap(0),
                ExamNetQtiPromptText(" efter."),
            )
        ),
    )
    assert len(body.gap_elements) == 1
    assert body.gap_elements[0].tag == _tag("qti-text-entry-interaction")
    assert body.image_elements == ()


def test_heading_paragraphs_keep_their_levels_and_text() -> None:
    item = _free_text(
        (
            ExamNetQtiPromptParagraph(
                heading_level=1, segments=(ExamNetQtiPromptText("Rubrik ett"),)
            ),
            ExamNetQtiPromptParagraph(
                heading_level=2, segments=(ExamNetQtiPromptText("Rubrik två"),)
            ),
            ExamNetQtiPromptParagraph(
                heading_level=3, segments=(ExamNetQtiPromptText("Rubrik tre"),)
            ),
            ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("Brödtext"),)),
        )
    )

    prompt = _prompt(_root(item))

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(heading_level=1, segments=(ExamNetQtiPromptText("Rubrik ett"),)),
        ExamNetQtiPromptParagraph(heading_level=2, segments=(ExamNetQtiPromptText("Rubrik två"),)),
        ExamNetQtiPromptParagraph(heading_level=3, segments=(ExamNetQtiPromptText("Rubrik tre"),)),
        ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("Brödtext"),)),
    )


def test_nested_marks_are_reordered_into_the_render_order() -> None:
    root = ElementTree.Element(_tag("qti-prompt"))
    paragraph = paragraph_element(root, None)
    outer = append_marked_text(paragraph, None, "fet", ("bold", "italic", "underline"))
    append_marked_text(paragraph, outer, " upp", ("superscript",))

    prompt = _roundtrip(root)

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptText("fet", ("bold", "italic", "underline")),
                ExamNetQtiPromptText(" upp", ("superscript",)),
            )
        ),
    )


def test_bold_text_with_a_line_break_merges_back_into_one_run() -> None:
    root = ElementTree.Element(_tag("qti-prompt"))
    paragraph = paragraph_element(root, None)
    append_marked_text(paragraph, None, "a\nb", ("bold",))

    prompt = _roundtrip(root)

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("a\nb", ("bold",)),)),
    )


def test_space_between_marked_runs_is_lost_by_the_writer_indentation() -> None:
    # Known writer loss: ElementTree.indent replaces the writer's plain " " tail
    # with "\n  ", so the exported XML no longer carries the space.
    root = ElementTree.Element(_tag("qti-prompt"))
    paragraph = paragraph_element(root, None)
    bold = append_marked_text(paragraph, None, "a", ("bold",))
    append_marked_text(paragraph, bold, " ", ())
    append_marked_text(paragraph, paragraph[-1], "b", ("italic",))

    prompt = _roundtrip(root)

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptText("a", ("bold",)),
                ExamNetQtiPromptText("b", ("italic",)),
            )
        ),
    )


def test_unindented_space_tail_between_marks_is_kept() -> None:
    prompt = ElementTree.fromstring(
        f'<qti-prompt xmlns="{QTI_NAMESPACE}"><p><strong>a</strong> <em>b</em></p></qti-prompt>'
    )

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptText("a", ("bold",)),
                ExamNetQtiPromptText(" "),
                ExamNetQtiPromptText("b", ("italic",)),
            )
        ),
    )


def test_line_break_between_different_marks_is_not_merged() -> None:
    root = ElementTree.Element(_tag("qti-prompt"))
    paragraph = paragraph_element(root, None)
    bold = append_marked_text(paragraph, None, "a", ("bold",))
    append_marked_text(paragraph, bold, "\nb", ("italic",))

    prompt = _roundtrip(root)

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptText("a", ("bold",)),
                ExamNetQtiPromptText("\n"),
                ExamNetQtiPromptText("b", ("italic",)),
            )
        ),
    )


def test_gaps_in_a_block_paragraph_keep_order_and_honour_offset() -> None:
    item = ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Före [___] och [___] efter.",),
        max_score=2,
        text_entry_gaps=(_gap(1, ("alfa",)), _gap(2, ("beta",))),
        prompt_paragraphs=(
            ExamNetQtiPromptParagraph(
                segments=(
                    ExamNetQtiPromptText("Före "),
                    ExamNetQtiPromptGap(0),
                    ExamNetQtiPromptText(" och "),
                    ExamNetQtiPromptGap(1),
                    ExamNetQtiPromptText(" efter."),
                )
            ),
        ),
    )

    body_element = _item_body(_root(item))

    body = read_rich_content(list(body_element), leading_text=body_element.text, gap_offset=5)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptText("Före "),
                ExamNetQtiPromptGap(5),
                ExamNetQtiPromptText(" och "),
                ExamNetQtiPromptGap(6),
                ExamNetQtiPromptText(" efter."),
            )
        ),
    )
    assert [element.tag for element in body.gap_elements] == [
        _tag("qti-text-entry-interaction"),
        _tag("qti-text-entry-interaction"),
    ]
    assert [element.attrib["response-identifier"] for element in body.gap_elements] == [
        "RESPONSE_gap_001",
        "RESPONSE_gap_002",
    ]


def test_images_keep_placement_and_honour_offset() -> None:
    item = _free_text(
        (
            ExamNetQtiPromptParagraph(
                segments=(
                    ExamNetQtiPromptImage(0),
                    ExamNetQtiPromptText(" möter "),
                    ExamNetQtiPromptImage(1),
                )
            ),
        ),
        image_resources=(_image(1, "Bild 1"), _image(2, "Bild 2")),
    )

    prompt = _prompt(_root(item, _IMAGE_PATHS))

    body = read_rich_content(list(prompt), leading_text=prompt.text, image_offset=3)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptImage(3),
                ExamNetQtiPromptText(" möter "),
                ExamNetQtiPromptImage(4),
            )
        ),
    )
    assert [element.attrib["src"] for element in body.image_elements] == list(_IMAGE_PATHS)
    assert body.gap_elements == ()


def test_inline_choice_interaction_is_recorded_without_descending() -> None:
    item = ExamNetQtiItem(
        item_id="q3",
        sequence=3,
        title="Välj",
        interaction_type=ExamNetQtiInteractionType.INLINE_CHOICE,
        prompt_lines=("Välj [___] nu.",),
        max_score=1,
        inline_choice_gaps=(
            ExamNetQtiInlineChoiceGap(
                response_identifier="RESPONSE_inline_001",
                options=(
                    ExamNetQtiChoice(identifier="A", text="Alfa"),
                    ExamNetQtiChoice(identifier="B", text="Beta"),
                ),
                correct_option_identifier="A",
            ),
        ),
        prompt_paragraphs=(
            ExamNetQtiPromptParagraph(
                segments=(
                    ExamNetQtiPromptText("Välj "),
                    ExamNetQtiPromptGap(0),
                    ExamNetQtiPromptText(" nu."),
                )
            ),
        ),
    )

    body_element = _item_body(_root(item))

    body = read_rich_content(list(body_element), leading_text=body_element.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptText("Välj "),
                ExamNetQtiPromptGap(0),
                ExamNetQtiPromptText(" nu."),
            )
        ),
    )
    assert len(body.gap_elements) == 1
    interaction = body.gap_elements[0]
    assert interaction.tag == _tag("qti-inline-choice-interaction")
    options = interaction.findall(_tag("qti-inline-choice"))
    assert [option.attrib["identifier"] for option in options] == ["A", "B"]
