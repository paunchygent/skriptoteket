"""Native formatting reaches the Exam.net QTI package as semantic XML elements.

Purpose:
    Prove TASK-SKRIPT-39-09-08 export: ``strong``, ``em``, ``u``, ``sup`` and
    ``sub`` and ``h1``-``h3`` are written for question prompts, exam and shared
    instructions, choice labels and matching entries, while the DigiExam lane's
    plain shared values keep the positionless rendering.

Relationships:
    - Exercises `domain.examnet_qti_export`, `domain.examnet_qti_prompt` and the
      shared item serialization with native documents built directly.
"""

from __future__ import annotations

import re
from decimal import Decimal
from uuid import uuid4
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_admissibility import (
    blocking_errors,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import QTI_NAMESPACE
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextMark,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit


def _tag(local_name: str) -> str:
    return f"{{{QTI_NAMESPACE}}}{local_name}"


def _text(text: str, *marks: NativeTextMark) -> NativeTextSegment:
    return NativeTextSegment(text=text, marks=marks)


def _paragraph(*segments: NativeSegment, heading_level: int | None = None) -> NativeParagraph:
    return NativeParagraph(segments=segments, heading_level=heading_level)


def _review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.TEACHER_CREATED,
    )


def _document(
    *items: NativeExamItem,
    instructions: tuple[NativeParagraph, ...] = (),
    parents: tuple[NativeExamParent, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Formateringsprov",
        instructions=instructions,
        items=items,
        parents=parents,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _free_text_item(*, sequence: int, body: tuple[NativeParagraph, ...]) -> NativeExamItem:
    return NativeExamItem(
        item_id=f"item_{sequence:03d}",
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        writing_lines=8,
        body=body,
        points=1,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=_review(),
    )


def _serialize(item: ExamNetQtiItem) -> tuple[str, ElementTree.Element]:
    xml_text = serialize_qti_assessment_item(item).decode("utf-8")
    return xml_text, ElementTree.fromstring(xml_text)


_EMPTY_PARAGRAPH = NativeParagraph(segments=(), heading_level=None)
_STRUCTURE = "<p>First<br/>Second</p><p/><p>Third</p>"


def _unformatted_structure(*marks: NativeTextMark) -> tuple[NativeParagraph, ...]:
    return (
        _paragraph(_text("First\nSecond", *marks)),
        _EMPTY_PARAGRAPH,
        _paragraph(_text("Third")),
    )


def _compact(xml_text: str) -> str:
    """The serialized markup without indentation or the pretty-printer's space before ``/>``."""
    return re.sub(r">\s+<", "><", xml_text).replace(" />", "/>")


class TestUnformattedStructure:
    """Hard breaks and empty paragraphs survive whether or not any run is marked."""

    @pytest.mark.parametrize("marks", [(), ("bold",)])
    def test_question_text_keeps_its_breaks_and_empty_paragraph(
        self, marks: tuple[NativeTextMark, ...]
    ) -> None:
        item = _free_text_item(sequence=1, body=_unformatted_structure(*marks))
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item))

        xml_text, _ = _serialize(qti_item)

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
        item = _free_text_item(sequence=1, body=(_paragraph(_text("Fråga.")),))
        document = _document(item, instructions=_unformatted_structure())
        (qti_item,) = native_exam_to_examnet_qti_items(document)

        xml_text, _ = _serialize(qti_item)

        assert f"<qti-prompt>{_STRUCTURE}<p>Fråga.</p></qti-prompt>" in _compact(xml_text)
        assert blocking_errors((qti_item,)) == ()

    def test_part_instruction_of_one_child_keeps_its_breaks_in_the_child_prompt(self) -> None:
        item = _free_text_item(sequence=1, body=(_paragraph(_text("Fråga.")),))
        parent = NativeExamParent(
            parent_id="parent_001",
            instruction=_unformatted_structure(),
            item_ids=("item_001",),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item, parents=(parent,)))

        xml_text, _ = _serialize(qti_item)

        assert f"<qti-prompt>{_STRUCTURE}<p>Fråga.</p></qti-prompt>" in _compact(xml_text)
        assert blocking_errors((qti_item,)) == ()

    def test_part_instruction_of_several_children_keeps_its_breaks_in_the_shared_stem(
        self,
    ) -> None:
        children = (
            _free_text_item(sequence=1, body=(_paragraph(_text("Fråga ett.")),)),
            _free_text_item(sequence=2, body=(_paragraph(_text("Fråga två.")),)),
        )
        parent = NativeExamParent(
            parent_id="parent_001",
            instruction=_unformatted_structure(),
            item_ids=("item_001", "item_002"),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(*children, parents=(parent,)))

        xml_text, _ = _serialize(qti_item)

        assert qti_item.children
        assert f"<qti-item-body>{_STRUCTURE}<qti-extended-text" in _compact(xml_text)
        assert blocking_errors((qti_item,)) == ()


class TestPromptFormatting:
    def test_prompt_writes_every_mark_and_heading_level_as_an_element(self) -> None:
        item = _free_text_item(
            sequence=1,
            body=(
                _paragraph(_text("Rubrik"), heading_level=1),
                _paragraph(
                    _text("fet", "bold"),
                    _text(" kursiv", "italic"),
                    _text(" understruken", "underline"),
                    _text(" upp", "superscript"),
                    _text(" ner", "subscript"),
                ),
            ),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item))

        xml_text, root = _serialize(qti_item)

        prompt = root.find(f".//{_tag('qti-prompt')}")
        assert prompt is not None
        heading = prompt.find(_tag("h1"))
        assert heading is not None
        assert heading.text == "Rubrik"
        assert [element.text for element in prompt.findall(f".//{_tag('strong')}")] == ["fet"]
        assert [element.text for element in prompt.findall(f".//{_tag('em')}")] == [" kursiv"]
        assert [element.text for element in prompt.findall(f".//{_tag('u')}")] == [" understruken"]
        assert [element.text for element in prompt.findall(f".//{_tag('sup')}")] == [" upp"]
        assert [element.text for element in prompt.findall(f".//{_tag('sub')}")] == [" ner"]
        assert "&lt;strong&gt;" not in xml_text

    def test_marks_nest_in_the_fixed_canonical_order(self) -> None:
        item = _free_text_item(
            sequence=1,
            body=(_paragraph(_text("både", "italic", "bold")),),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item))

        _, root = _serialize(qti_item)

        strong = root.find(f".//{_tag('strong')}")
        assert strong is not None
        emphasis = strong.find(_tag("em"))
        assert emphasis is not None
        assert emphasis.text == "både"

    def test_three_marks_nest_around_the_run_and_the_following_run_follows(self) -> None:
        item = _free_text_item(
            sequence=1,
            body=(
                _paragraph(
                    _text("tre", "bold", "italic", "underline"),
                    _text(" efter"),
                ),
            ),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item))

        _, root = _serialize(qti_item)

        prompt = root.find(f".//{_tag('qti-prompt')}")
        assert prompt is not None
        assert [child.tag for child in prompt] == [_tag("strong")]
        strong = prompt.find(_tag("strong"))
        assert strong is not None
        assert [child.tag for child in strong] == [_tag("em")]
        emphasis = strong.find(_tag("em"))
        assert emphasis is not None
        assert [child.tag for child in emphasis] == [_tag("u")]
        underline = emphasis.find(_tag("u"))
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
                _paragraph(
                    _text("fyra", "bold", "italic", "underline", "superscript"),
                    _text(" efter", "subscript"),
                ),
            ),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item))

        _, root = _serialize(qti_item)

        prompt = root.find(f".//{_tag('qti-prompt')}")
        assert prompt is not None
        strong, subscript = list(prompt)
        assert strong.tag == _tag("strong")
        assert subscript.tag == _tag("sub")
        assert subscript.text == " efter"
        assert [child.tag for child in strong] == [_tag("em")]
        emphasis = strong.find(_tag("em"))
        assert emphasis is not None
        assert [child.tag for child in emphasis] == [_tag("u")]
        underline = emphasis.find(_tag("u"))
        assert underline is not None
        assert [child.tag for child in underline] == [_tag("sup")]
        superscript = underline.find(_tag("sup"))
        assert superscript is not None
        assert superscript.text == "fyra"
        assert list(superscript) == []

    def test_gap_fill_marks_render_and_the_gap_itself_carries_no_markup(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.GAP_FILL,
            body=(
                _paragraph(
                    _text("Fet ", "bold"),
                    NativeGapSegment(gap_id="gap_001"),
                    _text(" kursiv", "italic"),
                ),
            ),
            points=1,
            gaps=(NativeGap(gap_id="gap_001", accepted_values=("svar",)),),
            answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
            review=_review(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item))

        _, root = _serialize(qti_item)

        body = root.find(_tag("qti-item-body"))
        assert body is not None
        paragraph = body.find(_tag("p"))
        assert paragraph is not None
        strong = paragraph.find(_tag("strong"))
        assert strong is not None
        assert strong.text == "Fet "
        emphasis = paragraph.find(_tag("em"))
        assert emphasis is not None
        assert emphasis.text == " kursiv"
        gap = paragraph.find(_tag("qti-text-entry-interaction"))
        assert gap is not None
        assert list(gap) == []


class TestInstructionFormatting:
    def test_exam_and_parent_instructions_render_headings_and_marks(self) -> None:
        children = (
            _free_text_item(sequence=1, body=(_paragraph(_text("Fråga ett.")),)),
            _free_text_item(sequence=2, body=(_paragraph(_text("Fråga två.")),)),
        )
        parent = NativeExamParent(
            parent_id="parent_001",
            instruction=(
                _paragraph(_text("Gäller alla delar."), heading_level=2),
                _paragraph(_text("Läs ", "bold"), _text("noggrant.", "italic")),
            ),
            item_ids=("item_001", "item_002"),
        )
        document = _document(
            *children,
            instructions=(
                _paragraph(_text("Svenska 2"), heading_level=1),
                _paragraph(
                    _text("Instruktion med ", "underline"), _text("markering.", "superscript")
                ),
            ),
            parents=(parent,),
        )

        (qti_item,) = native_exam_to_examnet_qti_items(document)

        _, root = _serialize(qti_item)

        assert qti_item.children
        item_body = root.find(_tag("qti-item-body"))
        assert item_body is not None
        assert [element.text for element in item_body.findall(f".//{_tag('h1')}")] == ["Svenska 2"]
        assert [element.text for element in item_body.findall(f".//{_tag('h2')}")] == [
            "Gäller alla delar."
        ]
        assert [element.text for element in item_body.findall(f".//{_tag('strong')}")] == ["Läs "]
        assert [element.text for element in item_body.findall(f".//{_tag('em')}")] == ["noggrant."]
        assert [element.text for element in item_body.findall(f".//{_tag('u')}")] == [
            "Instruktion med "
        ]
        assert [element.text for element in item_body.findall(f".//{_tag('sup')}")] == [
            "markering."
        ]


class TestChoiceAndMatchFormatting:
    def test_choice_labels_render_marks_and_headings_and_keep_a_plain_label(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            body=(_paragraph(_text("Välj.")),),
            points=1,
            choices=(
                NativeChoice(
                    choice_id="choice_001",
                    body=(
                        _paragraph(_text("fet", "bold"), _text(" två", "italic"), heading_level=2),
                    ),
                ),
                NativeChoice(choice_id="choice_002", body=(_paragraph(_text("vanlig")),)),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct_choice_ids=("choice_001",),
            ),
            review=_review(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item))

        assert [choice.text for choice in qti_item.choices] == ["fet två", "vanlig"]
        _, root = _serialize(qti_item)

        choices = root.findall(f".//{_tag('qti-simple-choice')}")
        assert len(choices) == 2
        rich, plain = choices
        rich_heading = rich.find(_tag("h2"))
        strong = rich.find(f".//{_tag('strong')}")
        emphasis = rich.find(f".//{_tag('em')}")
        plain_paragraph = plain.find(_tag("p"))
        assert rich_heading is not None
        assert strong is not None and strong.text == "fet"
        assert emphasis is not None and emphasis.text == " två"
        assert plain_paragraph is not None and plain_paragraph.text == "vanlig"

    def test_matching_entries_render_marks_and_keep_a_plain_label(self) -> None:
        item = NativeExamItem(
            item_id="item_001",
            sequence=1,
            kind=NativeExamItemKind.MATCHING,
            body=(_paragraph(_text("Matcha.")),),
            points=1,
            tick_points=Decimal("1"),
            match_left=(
                NativeMatchLeft(
                    left_id="left_001",
                    body=(_paragraph(_text("A", "bold")),),
                ),
            ),
            match_right=(
                NativeMatchRight(
                    right_id="right_001",
                    body=(_paragraph(_text("ett", "italic")),),
                ),
                NativeMatchRight(right_id="right_002", body=(_paragraph(_text("två")),)),
            ),
            answer_key=NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                match_pairs=(NativeMatchPair(left_id="left_001", right_id="right_001"),),
            ),
            review=_review(),
        )
        (qti_item,) = native_exam_to_examnet_qti_items(_document(item))

        assert [entry.text for entry in qti_item.match_left] == ["A"]
        assert [entry.text for entry in qti_item.match_right] == ["ett", "två"]
        _, root = _serialize(qti_item)

        entries = root.findall(f".//{_tag('qti-simple-associable-choice')}")
        assert len(entries) == 3
        left, right = entries[0], entries[1]
        strong = left.find(f".//{_tag('strong')}")
        emphasis = right.find(f".//{_tag('em')}")
        plain_paragraph = entries[2].find(_tag("p"))
        assert strong is not None and strong.text == "A"
        assert emphasis is not None and emphasis.text == "ett"
        assert plain_paragraph is not None and plain_paragraph.text == "två"


class TestPlainSharedValues:
    def test_shared_defaults_stay_empty_for_the_digiexam_lane(self) -> None:
        assert ExamNetQtiPromptText("x").marks == ()
        paragraph = ExamNetQtiPromptParagraph(segments=(ExamNetQtiPromptText("x"),))
        assert paragraph.heading_level is None
        assert ExamNetQtiChoice("choice_001", "Ett").body == ()
        assert ExamNetQtiMatchEntry("left_001", "A").body == ()

    def test_a_plain_shared_choice_renders_positionless_text(self) -> None:
        item = ExamNetQtiItem(
            item_id="q1",
            sequence=1,
            title="Fråga 1",
            interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
            prompt_lines=("Välj ett.",),
            max_score=1,
            evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
            choices=(ExamNetQtiChoice("choice_001", "Ett"), ExamNetQtiChoice("choice_002", "Två")),
            correct_choice_identifiers=("choice_001",),
        )

        _, root = _serialize(item)

        choices = root.findall(f".//{_tag('qti-simple-choice')}")
        assert [choice.text for choice in choices] == ["Ett", "Två"]
        assert [list(choice) for choice in choices] == [[], []]
