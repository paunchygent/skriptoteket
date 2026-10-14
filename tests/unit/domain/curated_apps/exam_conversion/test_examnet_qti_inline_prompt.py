"""Rich prompt placement tests for Exam.net QTI item serialization.

Purpose:
    Prove that ``prompt_paragraphs`` render text, images, and gaps at their
    source position in interaction prompts and gap-fill bodies, keep the
    positionless append behaviour for other producers, and fail closed on
    out-of-range or repeated segment indexes.

Relationships:
    - Exercises `domain.examnet_qti_item_xml` and `domain.examnet_qti_xml`
      with contract items built directly, without DigiExam or native adapters.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptGap,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptText,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import QTI_NAMESPACE

pytestmark = pytest.mark.unit

_IMAGE_PATHS = ("../resources/q1-image_001.png", "../resources/q1-image_002.png")


def _tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _root(item: ExamNetQtiItem, image_paths: tuple[str, ...] = ()) -> ElementTree.Element:
    return ElementTree.fromstring(serialize_qti_assessment_item(item, image_paths=image_paths))


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


def test_rich_free_text_prompt_places_the_image_between_its_text_runs() -> None:
    item = ExamNetQtiItem(
        item_id="q1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Beskriv bilden.",),
        max_score=1,
        prompt_paragraphs=(
            (
                ExamNetQtiPromptText("Beskriv: "),
                ExamNetQtiPromptImage(0),
                ExamNetQtiPromptText(" noggrant."),
            ),
        ),
        image_resources=(_image(1, "Bild 1"),),
    )

    root = _root(item, (_IMAGE_PATHS[0],))

    prompt = root.find(f".//{_tag('prompt')}")
    assert prompt is not None
    assert prompt.text == "Beskriv: "
    assert [child.tag for child in prompt] == [_tag("img")]
    assert prompt[0].attrib == {"src": _IMAGE_PATHS[0], "alt": "Bild 1"}
    assert prompt[0].tail == " noggrant."
    assert "Beskriv bilden." not in ElementTree.tostring(root, encoding="unicode")


def test_rich_prompt_repeated_image_occurrences_use_their_own_resource_index() -> None:
    item = ExamNetQtiItem(
        item_id="q1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Jämför bilderna.",),
        max_score=1,
        prompt_paragraphs=(
            (
                ExamNetQtiPromptImage(0),
                ExamNetQtiPromptText(" möter "),
                ExamNetQtiPromptImage(1),
            ),
        ),
        image_resources=(_image(1, "Bild 1"), _image(2, "Bild 2")),
    )

    root = _root(item, _IMAGE_PATHS)

    prompt = root.find(f".//{_tag('prompt')}")
    assert prompt is not None
    assert [child.attrib["src"] for child in prompt] == list(_IMAGE_PATHS)
    assert [child.attrib["alt"] for child in prompt] == ["Bild 1", "Bild 2"]
    assert prompt[0].tail == " möter "
    assert (prompt[1].tail or "").strip() == ""


def test_rich_gap_fill_body_keeps_gap_and_image_segment_order() -> None:
    item = ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Före [___] och [___] efter.",),
        max_score=2,
        text_entry_gaps=(_gap(1, ("alfa",)), _gap(2, ("beta",))),
        prompt_paragraphs=(
            (
                ExamNetQtiPromptText("Före "),
                ExamNetQtiPromptGap(0),
                ExamNetQtiPromptText(" och "),
                ExamNetQtiPromptGap(1),
                ExamNetQtiPromptText(" med "),
                ExamNetQtiPromptImage(0),
                ExamNetQtiPromptText(" efter."),
            ),
        ),
        image_resources=(_image(1, "Bild 1"),),
    )

    root = _root(item, (_IMAGE_PATHS[0],))

    body = root.find(_tag("itemBody"))
    assert body is not None
    paragraphs = body.findall(_tag("p"))
    assert len(paragraphs) == 1
    paragraph = paragraphs[0]
    assert paragraph.text == "Före "
    children = list(paragraph)
    assert [child.tag for child in children] == [
        _tag("textEntryInteraction"),
        _tag("textEntryInteraction"),
        _tag("img"),
    ]
    assert [child.attrib["responseIdentifier"] for child in children[:2]] == [
        "RESPONSE_gap_001",
        "RESPONSE_gap_002",
    ]
    assert [child.attrib["expectedLength"] for child in children[:2]] == ["8", "8"]
    assert children[0].tail == " och "
    assert children[1].tail == " med "
    assert children[2].attrib == {"src": _IMAGE_PATHS[0], "alt": "Bild 1"}
    assert children[2].tail == " efter."
    assert root.findall(f".//{_tag('img')}") == [children[2]]


def test_rich_gap_fill_body_appends_only_unplaced_gaps() -> None:
    item = ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Fyll i [___] och [___].",),
        max_score=2,
        text_entry_gaps=(_gap(1, ("alfa",)), _gap(2, ("beta",))),
        prompt_paragraphs=((ExamNetQtiPromptText("Endast "), ExamNetQtiPromptGap(0)),),
    )

    root = _root(item)

    body = root.find(_tag("itemBody"))
    assert body is not None
    paragraphs = body.findall(_tag("p"))
    assert len(paragraphs) == 2
    assert paragraphs[0].text == "Endast "
    assert paragraphs[0][0].attrib["responseIdentifier"] == "RESPONSE_gap_001"
    assert paragraphs[1].text == "Lucka 2: "
    assert paragraphs[1][0].attrib["responseIdentifier"] == "RESPONSE_gap_002"


def test_rich_gap_fill_child_uses_qualified_response_identifiers() -> None:
    child = ExamNetQtiItem(
        item_id="child_1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=(),
        max_score=1,
        text_entry_gaps=(_gap(1, ("alfa",)),),
        prompt_paragraphs=(
            (
                ExamNetQtiPromptText("Svara: "),
                ExamNetQtiPromptGap(0),
                ExamNetQtiPromptText(" här."),
            ),
        ),
    )
    parent = ExamNetQtiItem(
        item_id="parent_1",
        sequence=1,
        title="Fråga 1-1",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Läs instruktionen.",),
        max_score=1,
        instruction_lines=("Läs instruktionen.",),
        children=(child,),
    )

    root = _root(parent)

    declarations = root.findall(_tag("responseDeclaration"))
    assert [declaration.attrib["identifier"] for declaration in declarations] == [
        "child_1_SEPARATOR",
        "child_1_RESPONSE_gap_001",
    ]
    entries = root.findall(f".//{_tag('textEntryInteraction')}")
    assert len(entries) == 1
    assert entries[0].attrib == {
        "responseIdentifier": "child_1_RESPONSE_gap_001",
        "expectedLength": "8",
    }
    assert entries[0].tail == " här."


def test_positionless_prompts_still_append_images() -> None:
    free_text = ExamNetQtiItem(
        item_id="q1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Beskriv bilden.",),
        max_score=1,
        image_resources=(_image(1, "Bild 1"),),
    )
    free_text_root = _root(free_text, (_IMAGE_PATHS[0],))

    prompt = free_text_root.find(f".//{_tag('prompt')}")
    assert prompt is not None
    assert prompt.text == "Beskriv bilden."
    assert [child.tag for child in prompt] == [_tag("img")]
    assert prompt[0].attrib["src"] == _IMAGE_PATHS[0]

    gap_fill = ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Fyll i [___].",),
        max_score=1,
        text_entry_gaps=(_gap(1, ("alfa",)),),
        image_resources=(_image(1, "Bild 1"),),
    )
    gap_fill_root = _root(gap_fill, (_IMAGE_PATHS[0],))

    body = gap_fill_root.find(_tag("itemBody"))
    assert body is not None
    paragraphs = body.findall(_tag("p"))
    assert len(paragraphs) == 2
    assert paragraphs[0].text == "Fyll i "
    assert paragraphs[0][0].tag == _tag("textEntryInteraction")
    assert paragraphs[1][0].tag == _tag("img")
    assert paragraphs[1][0].attrib["src"] == _IMAGE_PATHS[0]


def test_rich_multiple_paragraphs_use_p_children_and_lf_breaks_use_br() -> None:
    item = ExamNetQtiItem(
        item_id="q1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Rad ett", "Rad två"),
        max_score=1,
        prompt_paragraphs=(
            (ExamNetQtiPromptText("Rad ett\nRad två"),),
            (ExamNetQtiPromptImage(0), ExamNetQtiPromptText(" efter bilden")),
        ),
        image_resources=(_image(1, "Bild 1"),),
    )

    root = _root(item, (_IMAGE_PATHS[0],))

    prompt = root.find(f".//{_tag('prompt')}")
    assert prompt is not None
    assert (prompt.text or "").strip() == ""
    paragraphs = prompt.findall(_tag("p"))
    assert len(paragraphs) == 2
    first, second = paragraphs
    assert first.text == "Rad ett"
    breaks = first.findall(_tag("br"))
    assert len(breaks) == 1
    assert breaks[0].tail == "Rad två"
    assert second[0].tag == _tag("img")
    assert second[0].attrib["src"] == _IMAGE_PATHS[0]
    assert second[0].tail == " efter bilden"


@pytest.mark.parametrize("image_index", [-1, 1])
def test_out_of_range_prompt_image_index_fails_closed(image_index: int) -> None:
    item = ExamNetQtiItem(
        item_id="q1",
        sequence=1,
        title="Fråga 1",
        interaction_type=ExamNetQtiInteractionType.FREE_TEXT,
        prompt_lines=("Beskriv bilden.",),
        max_score=1,
        prompt_paragraphs=((ExamNetQtiPromptImage(image_index),),),
        image_resources=(_image(1, "Bild 1"),),
    )

    with pytest.raises(ValueError, match="image index"):
        _root(item, (_IMAGE_PATHS[0],))


@pytest.mark.parametrize("gap_index", [-1, 1])
def test_out_of_range_prompt_gap_index_fails_closed(gap_index: int) -> None:
    item = ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Fyll i [___].",),
        max_score=1,
        text_entry_gaps=(_gap(1, ("alfa",)),),
        prompt_paragraphs=((ExamNetQtiPromptGap(gap_index),),),
    )

    with pytest.raises(ValueError, match="gap index"):
        _root(item)


def test_repeated_prompt_gap_index_fails_closed() -> None:
    item = ExamNetQtiItem(
        item_id="q2",
        sequence=2,
        title="Lucktext",
        interaction_type=ExamNetQtiInteractionType.GAP_FILL,
        prompt_lines=("Fyll i [___].",),
        max_score=1,
        text_entry_gaps=(_gap(1, ("alfa",)),),
        prompt_paragraphs=(
            (ExamNetQtiPromptGap(0),),
            (ExamNetQtiPromptText(" igen "), ExamNetQtiPromptGap(0)),
        ),
    )

    with pytest.raises(ValueError, match="more than once"):
        _root(item)
