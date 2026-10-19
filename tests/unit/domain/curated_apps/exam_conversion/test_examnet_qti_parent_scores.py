"""Child-point tests for the QTI parent item reader.

Purpose:
    Prove that each parent child recovers its own points from its response
    declaration, mapping or the parent remainder, never by guessing.

Relationships:
    - Split from `test_examnet_qti_parent_reader.py`; shared builders live in
      `examnet_qti_reader_test_support` and are imported, never copied.
"""

from __future__ import annotations

from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    child_projection as _child_projection,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_document as _document,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_export as _export,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_gap_fill_child as _gap_fill_child,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_of as _parent,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_read as _read,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_round_trip as _round_trip,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    qti_tag as _tag,
)
from tests.unit.domain.curated_apps.exam_workspace.examnet_qti_export_test_support import (
    review_complete,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_single_choice_item,
    plain_body,
)

pytestmark = pytest.mark.unit


def _unkeyed_choice_child(*, sequence: int, item_id: str, points: int) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=plain_body(f"Välj ett alternativ för fråga {sequence}."),
        points=points,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
            NativeChoice(choice_id="choice_002", body=plain_body("Två")),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT),
        review=review_complete(),
    )


# --- child points ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("points", "expected"),
    [(0.99, 0.99), (1, 1), (1.01, 1.01)],
)
def test_a_gap_child_takes_its_points_from_the_parent_remainder(
    points: float, expected: float
) -> None:
    gap = _gap_fill_child(sequence=1, item_id="item_001", points=points, gap_count=3)
    other = make_single_choice_item(sequence=2, item_id="item_002")
    document = _document((gap, other), parent=_parent((gap, other)))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert exported.max_score == pytest.approx(points + 1)
    gap_child, choice_child = parent.children
    assert gap_child.max_score == expected
    assert type(gap_child.max_score) is type(expected)
    assert choice_child.max_score == 1


def test_an_inline_choice_child_recovers_its_points_from_its_gap_shares() -> None:
    child = inline_choice_item(sequence=1)
    child = child.model_copy(update={"points": 3})
    document = _document((child,), parent=_parent((child,)))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    (read_child,) = parent.children
    assert read_child.max_score == 3
    assert _child_projection(read_child) == _child_projection(exported.children[0])


def test_a_child_without_a_key_takes_the_parents_remainder() -> None:
    children = (
        make_single_choice_item(sequence=1, item_id="item_001"),
        _unkeyed_choice_child(sequence=2, item_id="item_002", points=2),
    )
    document = _document(children, parent=_parent(children))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert exported.max_score == 3
    keyed, unkeyed = parent.children
    assert keyed.max_score == 1
    assert unkeyed.max_score == 2


def test_two_children_without_keys_keep_no_points() -> None:
    children = (
        make_single_choice_item(sequence=1, item_id="item_001"),
        _unkeyed_choice_child(sequence=2, item_id="item_002", points=2),
        _unkeyed_choice_child(sequence=3, item_id="item_003", points=3),
    )
    document = _document(children, parent=_parent(children))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert exported.max_score == 6
    assert [child.max_score for child in parent.children] == [1, None, None]


def test_the_three_scoring_routes_read_their_own_points() -> None:
    read = _read(_manual_parent_xml())

    assert len(read) == 1
    (parent,) = read
    assert isinstance(parent, ExamNetQtiItem)
    assert parent.max_score == 11
    # Review 596c1654 F4: the gap child's rounded share states no total and the
    # unkeyed free-text child states none either, so both keep None.
    assert [child.max_score for child in parent.children] == [3, None, 2, None]


def _manual_parent_xml() -> bytes:
    """One parent whose three scoring routes disagree: all-or-nothing, mapping, remainder."""

    root = ElementTree.Element(
        _tag("qti-assessment-item"), {"identifier": "item_001", "title": "Del B"}
    )
    first = ElementTree.SubElement(
        root,
        _tag("qti-response-declaration"),
        {"identifier": "FIRST", "cardinality": "multiple", "base-type": "identifier"},
    )
    correct = ElementTree.SubElement(first, _tag("qti-correct-response"))
    for value in ("choice_001", "choice_002"):
        ElementTree.SubElement(correct, _tag("qti-value")).text = value
    for gap_identifier in ("G1", "G2"):
        declaration = ElementTree.SubElement(
            root,
            _tag("qti-response-declaration"),
            {"identifier": gap_identifier, "cardinality": "single", "base-type": "string"},
        )
        mapping = ElementTree.SubElement(
            declaration,
            _tag("qti-mapping"),
            {"default-value": "0", "lower-bound": "0", "upper-bound": "1"},
        )
        ElementTree.SubElement(
            mapping,
            _tag("qti-map-entry"),
            {"map-key": f"svar-{gap_identifier}", "mapped-value": "1"},
        )
    mapped = ElementTree.SubElement(
        root,
        _tag("qti-response-declaration"),
        {"identifier": "MAPPED", "cardinality": "single", "base-type": "identifier"},
    )
    mapped_correct = ElementTree.SubElement(mapped, _tag("qti-correct-response"))
    ElementTree.SubElement(mapped_correct, _tag("qti-value")).text = "choice_001"
    mapped_mapping = ElementTree.SubElement(
        mapped,
        _tag("qti-mapping"),
        {"default-value": "0", "lower-bound": "0", "upper-bound": "2"},
    )
    ElementTree.SubElement(
        mapped_mapping,
        _tag("qti-map-entry"),
        {"map-key": "choice_001", "mapped-value": "2"},
    )
    ElementTree.SubElement(
        root,
        _tag("qti-response-declaration"),
        {"identifier": "SECOND", "cardinality": "single", "base-type": "string"},
    )
    outcome = ElementTree.SubElement(
        root,
        _tag("qti-outcome-declaration"),
        {"identifier": "MAXSCORE", "cardinality": "single", "base-type": "float"},
    )
    default_value = ElementTree.SubElement(outcome, _tag("qti-default-value"))
    ElementTree.SubElement(default_value, _tag("qti-value")).text = "11"
    processing = ElementTree.SubElement(root, _tag("qti-response-processing"))
    condition = ElementTree.SubElement(processing, _tag("qti-response-condition"))
    response_if = ElementTree.SubElement(condition, _tag("qti-response-if"))
    match = ElementTree.SubElement(response_if, _tag("qti-match"))
    ElementTree.SubElement(match, _tag("qti-variable"), {"identifier": "FIRST"})
    ElementTree.SubElement(match, _tag("qti-correct"), {"identifier": "FIRST"})
    set_outcome = ElementTree.SubElement(
        response_if, _tag("qti-set-outcome-value"), {"identifier": "SCORE"}
    )
    total = ElementTree.SubElement(set_outcome, _tag("qti-sum"))
    ElementTree.SubElement(total, _tag("qti-variable"), {"identifier": "SCORE"})
    ElementTree.SubElement(total, _tag("qti-base-value"), {"base-type": "float"}).text = "3"
    mapped_condition = ElementTree.SubElement(processing, _tag("qti-response-condition"))
    mapped_if = ElementTree.SubElement(mapped_condition, _tag("qti-response-if"))
    not_null = ElementTree.SubElement(mapped_if, _tag("qti-not"))
    is_null = ElementTree.SubElement(not_null, _tag("qti-is-null"))
    ElementTree.SubElement(is_null, _tag("qti-variable"), {"identifier": "MAPPED"})
    mapped_set = ElementTree.SubElement(
        mapped_if, _tag("qti-set-outcome-value"), {"identifier": "SCORE"}
    )
    mapped_total = ElementTree.SubElement(mapped_set, _tag("qti-sum"))
    ElementTree.SubElement(mapped_total, _tag("qti-variable"), {"identifier": "SCORE"})
    ElementTree.SubElement(mapped_total, _tag("qti-map-response"), {"identifier": "MAPPED"})
    body = ElementTree.SubElement(root, _tag("qti-item-body"))
    instruction = ElementTree.SubElement(body, _tag("p"))
    instruction.text = "Gör alla deluppgifter."
    choice = ElementTree.SubElement(
        body,
        _tag("qti-choice-interaction"),
        {"response-identifier": "FIRST", "max-choices": "2"},
    )
    choice_prompt = ElementTree.SubElement(choice, _tag("qti-prompt"))
    ElementTree.SubElement(choice_prompt, _tag("p")).text = "Markera två."
    for identifier in ("choice_001", "choice_002"):
        simple = ElementTree.SubElement(
            choice, _tag("qti-simple-choice"), {"identifier": identifier}
        )
        simple.text = "Alt"
    ElementTree.SubElement(body, _tag("qti-gap-match-interaction"), {"response-identifier": "GAPS"})
    gap_paragraph = ElementTree.SubElement(body, _tag("p"))
    for gap_identifier in ("G1", "G2"):
        ElementTree.SubElement(
            gap_paragraph,
            _tag("qti-text-entry-interaction"),
            {"response-identifier": gap_identifier, "expected-length": "10"},
        )
    mapped_choice = ElementTree.SubElement(
        body,
        _tag("qti-choice-interaction"),
        {"response-identifier": "MAPPED", "max-choices": "1"},
    )
    mapped_prompt = ElementTree.SubElement(mapped_choice, _tag("qti-prompt"))
    ElementTree.SubElement(mapped_prompt, _tag("p")).text = "Välj ett."
    mapped_simple = ElementTree.SubElement(
        mapped_choice, _tag("qti-simple-choice"), {"identifier": "choice_001"}
    )
    mapped_simple.text = "Ett"
    extended = ElementTree.SubElement(
        body,
        _tag("qti-extended-text-interaction"),
        {"response-identifier": "SECOND", "expected-lines": "8"},
    )
    extended_prompt = ElementTree.SubElement(extended, _tag("qti-prompt"))
    ElementTree.SubElement(extended_prompt, _tag("p")).text = "Resonera."
    ElementTree.indent(root, space="  ")
    payload = ElementTree.tostring(root, encoding="utf-8")
    assert isinstance(payload, bytes)
    return payload
