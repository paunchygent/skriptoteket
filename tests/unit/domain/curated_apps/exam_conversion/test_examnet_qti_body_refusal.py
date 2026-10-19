"""Fail-closed tests for the Exam.net QTI rich-content reader.

Purpose:
    Prove that `examnet_qti_body_reader` refuses unsupported content with a
    typed error, drops writer-indentation whitespace deterministically, and
    that the public writer helpers round-trip through the same reader.

Relationships:
    - Split from `test_examnet_qti_body_reader.py`; shared builders live in
      `examnet_qti_reader_test_support` and are imported, never copied.
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
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptGap,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_inline_prompt import (
    append_gap_fill_body,
    append_interaction_prompt,
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
