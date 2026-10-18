"""Round-trip tests for the Exam.net QTI rich-content reader.

Purpose:
    Prove that `examnet_qti_body_reader` inverts the rich-content rendering of
    `examnet_qti_rich_text` and `examnet_qti_inline_prompt` from the parsed,
    indented XML the export writes: paragraphs, heading levels, nested marks,
    line breaks, images and gaps at their source position, and that unsupported
    content fails closed.

Relationships:
    - Exercises `domain.examnet_qti_body_reader` with writer-built elements
      serialized through `domain.examnet_qti_item_xml`, plus hand-written
      fail-closed fixtures.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_body_reader import (
    ExamNetQtiUnsupportedContent,
    paragraphs_plain_text,
    read_rich_content,
    read_text_paragraphs,
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
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_inline_prompt import (
    append_gap_fill_body,
    append_interaction_prompt,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_rich_text import (
    append_marked_text,
    paragraph_element,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE

pytestmark = pytest.mark.unit

_IMAGE_PATHS = ("images/q1-image_001.png", "images/q1-image_002.png")


def _tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _roundtrip(root: ElementTree.Element) -> ElementTree.Element:
    """Indent and serialize exactly as the export does, then parse back."""

    ElementTree.indent(root, space="  ")
    xml_bytes = ElementTree.tostring(root, encoding="utf-8")
    return ElementTree.fromstring(xml_bytes)


def _root(item: ExamNetQtiItem, image_paths: tuple[str, ...] = ()) -> ElementTree.Element:
    return ElementTree.fromstring(serialize_qti_assessment_item(item, image_paths=image_paths))


def _prompt(root: ElementTree.Element) -> ElementTree.Element:
    prompt = root.find(f".//{_tag('qti-prompt')}")
    assert prompt is not None
    return prompt


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


def _gap(number: int, accepted_values: tuple[str, ...]) -> ExamNetQtiTextEntryGap:
    return ExamNetQtiTextEntryGap(
        response_identifier=f"RESPONSE_gap_{number:03d}",
        label=f"Lucka {number}",
        accepted_values=accepted_values,
    )


def _free_text(
    paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    *,
    text_entry_gaps: tuple[ExamNetQtiTextEntryGap, ...] = (),
    image_resources: tuple[ExamNetQtiImageResource, ...] = (),
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id="q1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Beskriv.",),
        max_score=1,
        prompt_paragraphs=paragraphs,
        text_entry_gaps=text_entry_gaps,
        image_resources=image_resources,
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


def test_read_text_paragraphs_reads_a_plain_choice() -> None:
    choice = ElementTree.fromstring(
        f'<qti-simple-choice xmlns="{QTI_NAMESPACE}" identifier="A">Alfa</qti-simple-choice>'
    )

    assert read_text_paragraphs(choice) == (
        ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("Alfa"),)),
    )


def test_read_text_paragraphs_fails_closed_on_an_image() -> None:
    choice = ElementTree.fromstring(
        f'<qti-simple-choice xmlns="{QTI_NAMESPACE}" '
        f'identifier="A">Alfa<img src="x.png"/></qti-simple-choice>'
    )

    with pytest.raises(ExamNetQtiUnsupportedContent, match="img"):
        read_text_paragraphs(choice)


def test_read_text_paragraphs_fails_closed_on_a_gap() -> None:
    choice = ElementTree.fromstring(
        f'<qti-simple-choice xmlns="{QTI_NAMESPACE}" identifier="A">'
        f'Alfa<qti-text-entry-interaction response-identifier="R"/></qti-simple-choice>'
    )

    with pytest.raises(ExamNetQtiUnsupportedContent, match="qti-text-entry-interaction"):
        read_text_paragraphs(choice)


def test_whitespace_only_implicit_paragraph_is_dropped() -> None:
    prompt = ElementTree.fromstring(
        f'<qti-prompt xmlns="{QTI_NAMESPACE}">\n  <p>Brödtext</p>\n</qti-prompt>'
    )

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("Brödtext"),)),
    )


def test_leading_inline_content_before_a_block_forms_an_implicit_paragraph() -> None:
    prompt = ElementTree.fromstring(
        f'<qti-prompt xmlns="{QTI_NAMESPACE}">Före <p>Block</p></qti-prompt>'
    )

    body = read_rich_content(list(prompt), leading_text=prompt.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("Före"),)),
        ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("Block"),)),
    )


@pytest.mark.parametrize(
    ("name", "xml"),
    [
        ("table", f'<qti-prompt xmlns="{QTI_NAMESPACE}">före<table/>efter</qti-prompt>'),
        (
            "a",
            f'<qti-prompt xmlns="{QTI_NAMESPACE}">'
            f'före<a href="https://example.test">länk</a>efter</qti-prompt>',
        ),
        (
            "math",
            f'<qti-prompt xmlns="{QTI_NAMESPACE}">före<math><mi>x</mi></math>efter</qti-prompt>',
        ),
        (
            "widget",
            f'<qti-prompt xmlns="{QTI_NAMESPACE}" xmlns:x="http://example.test/x">'
            f"före<x:widget/>efter</qti-prompt>",
        ),
    ],
)
def test_unsupported_elements_fail_closed(name: str, xml: str) -> None:
    prompt = ElementTree.fromstring(xml)

    with pytest.raises(ExamNetQtiUnsupportedContent) as error:
        read_rich_content(list(prompt), leading_text=prompt.text)

    assert name in str(error.value)


def test_paragraphs_plain_text_renders_gaps_and_drops_images() -> None:
    paragraphs = (
        ExamNetQtiPromptParagraph(
            segments=(
                ExamNetQtiPromptText("Före "),
                ExamNetQtiPromptGap(0),
                ExamNetQtiPromptImage(0),
                ExamNetQtiPromptText(" efter."),
            )
        ),
        ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("Andra\nraden"),)),
    )

    assert paragraphs_plain_text(paragraphs) == "Före [___] efter.\nAndra raden"


def test_paragraphs_plain_text_returns_empty_for_no_paragraphs() -> None:
    assert paragraphs_plain_text(()) == ""


def test_public_interaction_prompt_writer_round_trips() -> None:
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
    body_element = ElementTree.Element(_tag("qti-item-body"))

    append_interaction_prompt(body_element, item, ())

    prompt = _prompt(_roundtrip(body_element))

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


def test_append_gap_fill_body_paragraphs_are_readable() -> None:
    item = ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=(),
        max_score=1,
        text_entry_gaps=(_gap(1, ("alfa",)),),
        prompt_paragraphs=(
            ExamNetQtiPromptParagraph(
                segments=(ExamNetQtiPromptText("Svara "), ExamNetQtiPromptGap(0))
            ),
        ),
    )
    body_element = ElementTree.Element(_tag("qti-item-body"))

    append_gap_fill_body(body_element, item, ())

    body_element = _roundtrip(body_element)
    body = read_rich_content(list(body_element), leading_text=body_element.text)

    assert body.paragraphs == (
        ExamNetQtiPromptParagraph(
            segments=(ExamNetQtiPromptText("Svara "), ExamNetQtiPromptGap(0))
        ),
    )
