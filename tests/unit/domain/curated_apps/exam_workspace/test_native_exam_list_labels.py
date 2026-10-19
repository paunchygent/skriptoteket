"""Workspace list labels mirror the frontend question list (user rule 2026-10-19)."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_list_labels import (
    native_exam_question_labels,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)


def _parent(parent_id: str, place: int, children: tuple[str, ...] = ()) -> NativeExamParent:
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
        NativeParagraph,
        NativeTextSegment,
    )

    return NativeExamParent(
        parent_id=parent_id,
        place=place,
        instruction=(
            NativeParagraph(
                heading_level=None,
                segments=(NativeTextSegment(text="Do these.", marks=()),),
            ),
        ),
        item_ids=children,
    )


def _document(items, parents=()) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=tuple(items),
        parents=tuple(parents),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def test_standalone_items_take_running_numbers():
    document = _document(
        [
            make_free_text_item(sequence=1, item_id="item_001"),
            make_free_text_item(sequence=2, item_id="item_002"),
            make_free_text_item(sequence=3, item_id="item_003"),
        ]
    )

    assert native_exam_question_labels(document) == {
        "item_001": "1",
        "item_002": "2",
        "item_003": "3",
    }


def test_part_children_take_letters_and_standalone_takes_next_number():
    document = _document(
        [
            make_free_text_item(sequence=1, item_id="item_001"),
            make_free_text_item(sequence=2, item_id="item_002"),
            make_free_text_item(sequence=3, item_id="item_003"),
            make_free_text_item(sequence=4, item_id="item_004"),
        ],
        parents=(_parent("parent_001", 0, ("item_001", "item_002", "item_003")),),
    )

    labels = native_exam_question_labels(document)

    assert labels["item_001"] == "1a"
    assert labels["item_002"] == "1b"
    assert labels["item_003"] == "1c"
    assert labels["item_004"] == "2"


def test_childless_part_takes_no_number():
    document = _document(
        [
            make_free_text_item(sequence=1, item_id="item_001"),
            make_free_text_item(sequence=2, item_id="item_002"),
        ],
        parents=(_parent("parent_001", 0),),
    )

    assert native_exam_question_labels(document) == {
        "item_001": "1",
        "item_002": "2",
    }


def test_two_parts_number_in_document_order():
    document = _document(
        [
            make_free_text_item(sequence=1, item_id="item_001"),
            make_free_text_item(sequence=2, item_id="item_002"),
            make_free_text_item(sequence=3, item_id="item_003"),
        ],
        parents=(
            _parent("parent_001", 0, ("item_001",)),
            _parent("parent_002", 1, ("item_002", "item_003")),
        ),
    )

    labels = native_exam_question_labels(document)

    assert labels["item_001"] == "1a"
    assert labels["item_002"] == "2a"
    assert labels["item_003"] == "2b"
