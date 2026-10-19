"""QTI import carries the free-text writing area (W2 round trip).

Proves that a free-text item's ``expected-lines`` survives the full path:
native export writes the writing lines, the real XML reader reads them back,
the import mapper restores them, and a re-export keeps the count. An absent
attribute takes the product default; a malformed one is an unsupported note,
never a crash.
"""

from uuid import uuid4
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
    MAX_WRITING_LINES,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiReadItem,
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_reader import (
    read_examnet_qti_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_xml import (
    QTI_NAMESPACE,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import import (
    build_native_exam_from_qti,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_paragraph,
    make_single_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.qti_import_mapping_support import (
    _SOURCE_SHA,
    _document,
)

pytestmark = pytest.mark.unit

_ITEM_PATH = "items/item_001.xml"


def _exported_free_text(*, writing_lines: int) -> ExamNetQtiItem:
    item = NativeExamItem.model_validate(
        {**dict(make_free_text_item()), "writing_lines": writing_lines}
    )
    (exported,) = native_exam_to_examnet_qti_items(_document((item,)))
    assert exported.expected_lines == writing_lines
    return exported


def _read(xml: bytes, *, sequence: int) -> tuple[ExamNetQtiReadItem, ...]:
    return read_examnet_qti_item(
        xml=xml,
        item_path=_ITEM_PATH,
        files={},
        sequence=sequence,
    )


def test_expected_lines_three_round_trips_as_writing_lines_three() -> None:
    xml = serialize_qti_assessment_item(_exported_free_text(writing_lines=3))

    (read,) = _read(xml, sequence=1)
    assert isinstance(read, ExamNetQtiItem)
    assert read.expected_lines == 3

    container = build_native_exam_from_qti(
        items=(read,),
        document_id=uuid4(),
        source_filename="skrivyta.zip",
        source_sha256=_SOURCE_SHA,
    )
    (imported,) = container.document.items
    assert imported.kind is NativeExamItemKind.FREE_TEXT
    assert imported.writing_lines == 3

    (re_exported,) = native_exam_to_examnet_qti_items(container.document)
    assert re_exported.expected_lines == 3


def test_absent_expected_lines_imports_the_product_default() -> None:
    xml = serialize_qti_assessment_item(_exported_free_text(writing_lines=3))
    root = ElementTree.fromstring(xml)
    interaction = root.find(f".//{{{QTI_NAMESPACE}}}qti-extended-text-interaction")
    assert interaction is not None
    del interaction.attrib["expected-lines"]
    stripped = ElementTree.tostring(root, encoding="utf-8")

    (read,) = _read(stripped, sequence=1)
    assert isinstance(read, ExamNetQtiItem)
    assert read.expected_lines == DEFAULT_WRITING_LINES

    container = build_native_exam_from_qti(
        items=(read,),
        document_id=uuid4(),
        source_filename="skrivyta-saknas.zip",
        source_sha256=_SOURCE_SHA,
    )
    assert container.document.items[0].writing_lines == DEFAULT_WRITING_LINES


@pytest.mark.parametrize("expected_lines", ["x", "0", str(MAX_WRITING_LINES + 1)])
def test_malformed_expected_lines_is_an_unsupported_note_not_a_crash(
    expected_lines: str,
) -> None:
    xml = serialize_qti_assessment_item(_exported_free_text(writing_lines=3))
    root = ElementTree.fromstring(xml)
    interaction = root.find(f".//{{{QTI_NAMESPACE}}}qti-extended-text-interaction")
    assert interaction is not None
    interaction.set("expected-lines", expected_lines)
    broken = ElementTree.tostring(root, encoding="utf-8")

    (unsupported,) = _read(broken, sequence=1)
    assert isinstance(unsupported, ExamNetQtiUnsupportedItem)
    assert unsupported.reason is ExamNetQtiUnsupportedReason.INTERACTION

    (sibling,) = native_exam_to_examnet_qti_items(_document((make_single_choice_item(),)))
    container = build_native_exam_from_qti(
        items=(unsupported, sibling),
        document_id=uuid4(),
        source_filename="skrivyta-fel.zip",
        source_sha256=_SOURCE_SHA,
    )

    assert [item.kind for item in container.document.items] == [NativeExamItemKind.SINGLE_CHOICE]
    assert container.notes == (
        "Fråga 1 – Resonera om renässansen.: frågetypen stöds inte och importerades inte.",
    )


def test_parent_free_text_child_keeps_its_expected_lines() -> None:
    first = make_free_text_item(sequence=1, item_id="item_001").model_copy(
        update={"writing_lines": 4}
    )
    second = make_free_text_item(sequence=2, item_id="item_002").model_copy(
        update={"writing_lines": 4}
    )
    parent = NativeExamParent(
        parent_id="parent_001",
        place=0,
        instruction=(make_paragraph("Gör alla deluppgifter."),),
        item_ids=("item_001", "item_002"),
    )
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=(first, second),
        parents=(parent,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    (exported,) = native_exam_to_examnet_qti_items(document)
    assert [child.expected_lines for child in exported.children] == [4, 4]

    xml = serialize_qti_assessment_item(exported)
    (read,) = _read(xml, sequence=1)
    assert isinstance(read, ExamNetQtiItem)
    assert [child.expected_lines for child in read.children] == [4, 4]

    container = build_native_exam_from_qti(
        items=(read,),
        document_id=uuid4(),
        source_filename="foralder-skrivyta.zip",
        source_sha256=_SOURCE_SHA,
    )
    assert [item.kind for item in container.document.items] == [
        NativeExamItemKind.FREE_TEXT,
        NativeExamItemKind.FREE_TEXT,
    ]
    assert [item.writing_lines for item in container.document.items] == [4, 4]
