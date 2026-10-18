"""Native formatting reaches the Exam.net QTI package as semantic XML elements.

Purpose:
    Prove TASK-SKRIPT-39-09-08 export: ``strong``, ``em``, ``u``, ``sup`` and
    ``sub`` and ``h1``-``h3`` are written for question prompts and exam and
    shared instructions, with hard breaks and empty paragraphs preserved.

Relationships:
    - Exercises `domain.examnet_qti_export`, `domain.examnet_qti_prompt` and the
      shared item serialization with native documents built directly.
    - Companions `test_examnet_qti_entry_formatting_export.py`, which owns
      choice-label, matching-entry and plain shared-value coverage.
"""

from __future__ import annotations

import re

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_admissibility import (
    blocking_errors,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextMark,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    document,
    paragraph,
    review_complete,
    serialize,
    tag,
    text,
)

pytestmark = pytest.mark.unit


def _free_text_item(*, sequence: int, body: tuple[NativeParagraph, ...]) -> NativeExamItem:
    return NativeExamItem(
        item_id=f"item_{sequence:03d}",
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        writing_lines=8,
        body=body,
        points=1,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=review_complete(),
    )


_EMPTY_PARAGRAPH = NativeParagraph(segments=(), heading_level=None)
_STRUCTURE = "<p>First<br/>Second</p><p/><p>Third</p>"


def _unformatted_structure(*marks: NativeTextMark) -> tuple[NativeParagraph, ...]:
    return (
        paragraph(text("First\nSecond", *marks)),
        _EMPTY_PARAGRAPH,
        paragraph(text("Third")),
    )


def _compact(xml_text: str) -> str:
    """The serialized markup without indentation or the pretty-printer's space before ``/>``."""
    return re.sub(r">\s+<", "><", xml_text).replace(" />", "/>")


class TestUnformattedStructure:
    """Hard breaks and empty paragraphs survive whether or not any run is marked."""

    @pytest.mark.parametrize("marks", [(), ("bold",)])
    def test_question_text_keeps_its_breaks_and_emptyparagraph(
        self, marks: tuple[NativeTextMark, ...]
    ) -> None:
        item = _free_text_item(sequence=1, body=_unformatted_structure(*marks))
        (qti_item,) = native_exam_to_examnet_qti_items(document(item))

        xml_text, _ = serialize(qti_item)

        compact = _compact(xml_text)
        if marks:
            assert (
                "<p><strong>First</strong><br/><strong>Second</strong></p><p/><p>Third</p>"
                in compact
            )
        else:
            assert f"<qti-prompt>{_STRUCTURE}</qti-prompt>" in compact
        assert blocking_errors((qti_item,)) == ()

    def test_exam_instruction_precedes_the_question_with_its_breaks(self) -> None:
        item = _free_text_item(sequence=1, body=(paragraph(text("Fråga.")),))
        exam_document = document(item, instructions=_unformatted_structure())
        (qti_item,) = native_exam_to_examnet_qti_items(exam_document)

        xml_text, _ = serialize(qti_item)

        assert f"<qti-prompt>{_STRUCTURE}<p>Fråga.</p></qti-prompt>" in _compact(xml_text)
        assert blocking_errors((qti_item,)) == ()

    def test_part_instruction_of_one_child_keeps_its_breaks_in_the_child_prompt(self) -> None:
        item = _free_text_item(sequence=1, body=(paragraph(text("Fråga.")),))
        parent = NativeExamParent(
            parent_id="parent_001",
            place=item.sequence - 1,
            instruction=_unformatted_structure(),
            item_ids=("item_001",),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(item, parents=(parent,)))

        xml_text, _ = serialize(qti_item)

        assert f"<qti-prompt>{_STRUCTURE}<p>Fråga.</p></qti-prompt>" in _compact(xml_text)
        assert blocking_errors((qti_item,)) == ()

    def test_part_instruction_of_several_children_keeps_its_breaks_in_the_shared_stem(
        self,
    ) -> None:
        children = (
            _free_text_item(sequence=1, body=(paragraph(text("Fråga ett.")),)),
            _free_text_item(sequence=2, body=(paragraph(text("Fråga två.")),)),
        )
        parent = NativeExamParent(
            parent_id="parent_001",
            place=children[0].sequence - 1,
            instruction=_unformatted_structure(),
            item_ids=("item_001", "item_002"),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(*children, parents=(parent,)))

        xml_text, _ = serialize(qti_item)

        assert qti_item.children
        assert f"<qti-item-body>{_STRUCTURE}<qti-extended-text" in _compact(xml_text)
        assert blocking_errors((qti_item,)) == ()


class TestPromptFormatting:
    def test_prompt_writes_every_mark_and_heading_level_as_an_element(self) -> None:
        item = _free_text_item(
            sequence=1,
            body=(
                paragraph(text("Rubrik"), heading_level=1),
                paragraph(
                    text("fet", "bold"),
                    text(" kursiv", "italic"),
                    text(" understruken", "underline"),
                    text(" upp", "superscript"),
                    text(" ner", "subscript"),
                ),
            ),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(item))

        xml_text, root = serialize(qti_item)

        prompt = root.find(f".//{tag('qti-prompt')}")
        assert prompt is not None
        heading = prompt.find(tag("h1"))
        assert heading is not None
        assert heading.text == "Rubrik"
        assert [element.text for element in prompt.findall(f".//{tag('strong')}")] == ["fet"]
        assert [element.text for element in prompt.findall(f".//{tag('em')}")] == [" kursiv"]
        assert [element.text for element in prompt.findall(f".//{tag('u')}")] == [" understruken"]
        assert [element.text for element in prompt.findall(f".//{tag('sup')}")] == [" upp"]
        assert [element.text for element in prompt.findall(f".//{tag('sub')}")] == [" ner"]
        assert "&lt;strong&gt;" not in xml_text

    def test_marks_nest_in_the_fixed_canonical_order(self) -> None:
        item = _free_text_item(
            sequence=1,
            body=(paragraph(text("både", "italic", "bold")),),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(item))

        _, root = serialize(qti_item)

        strong = root.find(f".//{tag('strong')}")
        assert strong is not None
        emphasis = strong.find(tag("em"))
        assert emphasis is not None
        assert emphasis.text == "både"

    def test_three_marks_nest_around_the_run_and_the_following_run_follows(self) -> None:
        item = _free_text_item(
            sequence=1,
            body=(
                paragraph(
                    text("tre", "bold", "italic", "underline"),
                    text(" efter"),
                ),
            ),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(item))

        _, root = serialize(qti_item)

        prompt = root.find(f".//{tag('qti-prompt')}")
        assert prompt is not None
        assert [child.tag for child in prompt] == [tag("strong")]
        strong = prompt.find(tag("strong"))
        assert strong is not None
        assert [child.tag for child in strong] == [tag("em")]
        emphasis = strong.find(tag("em"))
        assert emphasis is not None
        assert [child.tag for child in emphasis] == [tag("u")]
        underline = emphasis.find(tag("u"))
        assert underline is not None
        assert underline.text == "tre"
        assert list(underline) == []
        assert strong.tail is not None
        assert strong.tail.strip() == "efter"

    def test_four_marks_nest_around_the_run_and_keep_the_following_marked_run_in_order(
        self,
    ) -> None:
        item = _free_text_item(
            sequence=1,
            body=(
                paragraph(
                    text("fyra", "bold", "italic", "underline", "superscript"),
                    text(" efter", "subscript"),
                ),
            ),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(item))

        _, root = serialize(qti_item)

        prompt = root.find(f".//{tag('qti-prompt')}")
        assert prompt is not None
        strong, subscript = list(prompt)
        assert strong.tag == tag("strong")
        assert subscript.tag == tag("sub")
        assert subscript.text == " efter"
        assert [child.tag for child in strong] == [tag("em")]
        emphasis = strong.find(tag("em"))
        assert emphasis is not None
        assert [child.tag for child in emphasis] == [tag("u")]
        underline = emphasis.find(tag("u"))
        assert underline is not None
        assert [child.tag for child in underline] == [tag("sup")]
        superscript = underline.find(tag("sup"))
        assert superscript is not None
        assert superscript.text == "fyra"
        assert list(superscript) == []

    def test_gap_fill_marks_render_and_the_gap_itself_carries_no_markup(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                paragraph(
                    text("Fet ", "bold"),
                    NativeGapSegment(gap_id="gap_001"),
                    text(" kursiv", "italic"),
                ),
            ),
            points=1,
            gaps=(NativeGap(gap_id="gap_001", accepted_values=("svar",)),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
            review=review_complete(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(document(item))

        _, root = serialize(qti_item)

        body = root.find(tag("qti-item-body"))
        assert body is not None
        paragraph_element = body.find(tag("p"))
        assert paragraph_element is not None
        strong = paragraph_element.find(tag("strong"))
        assert strong is not None
        assert strong.text == "Fet "
        emphasis = paragraph_element.find(tag("em"))
        assert emphasis is not None
        assert emphasis.text == " kursiv"
        gap = paragraph_element.find(tag("qti-text-entry-interaction"))
        assert gap is not None
        assert list(gap) == []


class TestInstructionFormatting:
    def test_exam_and_parent_instructions_render_headings_and_marks(self) -> None:
        children = (
            _free_text_item(sequence=1, body=(paragraph(text("Fråga ett.")),)),
            _free_text_item(sequence=2, body=(paragraph(text("Fråga två.")),)),
        )
        parent = NativeExamParent(
            parent_id="parent_001",
            place=children[0].sequence - 1,
            instruction=(
                paragraph(text("Gäller alla delar."), heading_level=2),
                paragraph(text("Läs ", "bold"), text("noggrant.", "italic")),
            ),
            item_ids=("item_001", "item_002"),
        )
        exam_document = document(
            *children,
            instructions=(
                paragraph(text("Svenska 2"), heading_level=1),
                paragraph(text("Instruktion med ", "underline"), text("markering.", "superscript")),
            ),
            parents=(parent,),
        )

        (qti_item,) = native_exam_to_examnet_qti_items(exam_document)

        _, root = serialize(qti_item)

        assert qti_item.children
        item_body = root.find(tag("qti-item-body"))
        assert item_body is not None
        assert [element.text for element in item_body.findall(f".//{tag('h1')}")] == ["Svenska 2"]
        assert [element.text for element in item_body.findall(f".//{tag('h2')}")] == [
            "Gäller alla delar."
        ]
        assert [element.text for element in item_body.findall(f".//{tag('strong')}")] == ["Läs "]
        assert [element.text for element in item_body.findall(f".//{tag('em')}")] == ["noggrant."]
        assert [element.text for element in item_body.findall(f".//{tag('u')}")] == [
            "Instruktion med "
        ]
        assert [element.text for element in item_body.findall(f".//{tag('sup')}")] == ["markering."]
