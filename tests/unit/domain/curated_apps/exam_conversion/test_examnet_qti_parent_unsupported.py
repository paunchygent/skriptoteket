"""Unsupported-child tests for the QTI parent item reader.

Purpose:
    Prove that each unsupported parent child is skipped with its own note
    after the parent, while supported siblings keep their positions, points
    and image indexes.

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
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    imaged_choice as _imaged_choice,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    make_asset as _asset,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_document as _document,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_export as _export,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_of as _parent,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_read as _read,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    qti_tag as _tag,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_single_choice_item,
)

pytestmark = pytest.mark.unit

_PNG_A = b"\x89PNG\r\n\x1a\npayload-a"


# --- unsupported children ----------------------------------------------------------------


def _serialized_parent(*children: NativeExamItem) -> bytes:
    document = _document(children, parent=_parent(children))
    (exported,) = _export(document, assets_by_id={})
    return serialize_qti_assessment_item(exported)


def test_a_slider_child_is_skipped_with_one_note_after_the_parent() -> None:
    xml = _serialized_parent(
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    root = ElementTree.fromstring(xml)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    ElementTree.SubElement(
        body, _tag("qti-slider-interaction"), {"response-identifier": "item_003_RESPONSE"}
    )
    read = _read(ElementTree.tostring(root, encoding="utf-8"))

    assert len(read) == 2
    parent, note = read
    assert isinstance(parent, ExamNetQtiItem)
    assert len(parent.children) == 2
    assert isinstance(note, ExamNetQtiUnsupportedItem)
    assert note.sequence == parent.sequence == 1
    assert note.reason is ExamNetQtiUnsupportedReason.INTERACTION


def test_a_gap_inside_the_instruction_makes_the_whole_item_unsupported() -> None:
    xml = _serialized_parent(
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    root = ElementTree.fromstring(xml)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    paragraph = ElementTree.Element(_tag("p"))
    ElementTree.SubElement(
        paragraph, _tag("qti-text-entry-interaction"), {"response-identifier": "GAP"}
    )
    body.insert(0, paragraph)
    read = _read(ElementTree.tostring(root, encoding="utf-8"))

    assert len(read) == 1
    (unsupported,) = read
    assert isinstance(unsupported, ExamNetQtiUnsupportedItem)
    assert unsupported.reason is ExamNetQtiUnsupportedReason.INTERACTION


def test_a_picture_inside_the_instruction_makes_the_whole_item_unsupported() -> None:
    xml = _serialized_parent(
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    root = ElementTree.fromstring(xml)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    paragraph = ElementTree.Element(_tag("p"))
    ElementTree.SubElement(paragraph, _tag("img"), {"src": "images/missing.png", "alt": "Bild"})
    body.insert(0, paragraph)
    read = _read(ElementTree.tostring(root, encoding="utf-8"))

    assert len(read) == 1
    (unsupported,) = read
    assert isinstance(unsupported, ExamNetQtiUnsupportedItem)
    assert unsupported.reason is ExamNetQtiUnsupportedReason.IMAGE


def test_a_child_picture_that_cannot_be_resolved_skips_only_that_child() -> None:
    payloads = {"asset_00000000000000a1": _PNG_A}
    assets = (_asset("asset_00000000000000a1", _PNG_A, "image/png"),)
    children = (
        _imaged_choice(sequence=1, item_id="item_001", asset_id="asset_00000000000000a1"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    document = _document(children, parent=_parent(children), assets=assets)
    (exported,) = _export(document, assets_by_id=payloads)
    xml = serialize_qti_assessment_item(exported, image_paths=("images/parent_001-001.png",))
    read = _read(xml)

    assert len(read) == 2
    parent, note = read
    assert isinstance(parent, ExamNetQtiItem)
    assert len(parent.children) == 1
    assert isinstance(note, ExamNetQtiUnsupportedItem)
    assert note.sequence == parent.sequence
    assert note.reason is ExamNetQtiUnsupportedReason.IMAGE


def test_an_item_with_only_unsupported_children_returns_only_their_notes() -> None:
    root = ElementTree.Element(
        _tag("qti-assessment-item"), {"identifier": "item_001", "title": "Fråga"}
    )
    body = ElementTree.SubElement(root, _tag("qti-item-body"))
    ElementTree.SubElement(body, _tag("qti-slider-interaction"), {"response-identifier": "FIRST"})
    ElementTree.SubElement(body, _tag("qti-slider-interaction"), {"response-identifier": "SECOND"})
    read = _read(ElementTree.tostring(root, encoding="utf-8"), sequence=4)

    assert len(read) == 2
    assert all(isinstance(item, ExamNetQtiUnsupportedItem) for item in read)
    assert [item.sequence for item in read] == [4, 4]
    assert all(
        isinstance(item, ExamNetQtiUnsupportedItem)
        and item.reason is ExamNetQtiUnsupportedReason.INTERACTION
        for item in read
    )


def test_a_skipped_middle_child_keeps_the_later_children_positions() -> None:
    xml = _serialized_parent(
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_single_choice_item(sequence=2, item_id="item_002"),
    )
    root = ElementTree.fromstring(xml)
    body = root.find(_tag("qti-item-body"))
    assert body is not None
    slider = ElementTree.Element(_tag("qti-slider-interaction"), {"response-identifier": "EXTRA"})
    body.insert(2, slider)
    read = _read(ElementTree.tostring(root, encoding="utf-8"))

    assert len(read) == 2
    parent, note = read
    assert isinstance(parent, ExamNetQtiItem)
    assert [child.item_id for child in parent.children] == [
        "parent_001_child_1",
        "parent_001_child_3",
    ]
    assert [child.sequence for child in parent.children] == [1, 3]
    assert isinstance(note, ExamNetQtiUnsupportedItem)
    assert note.sequence == parent.sequence
