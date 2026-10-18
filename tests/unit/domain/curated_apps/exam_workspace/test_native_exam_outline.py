"""The ordering owner: document outline read and outline write (TASK-SKRIPT-39-06-10 R1)."""

from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_outline import (
    OutlinePart,
    OutlineQuestion,
    document_outline,
    outline_items_and_parts,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
)


def _instruction(text: str) -> tuple[NativeParagraph, ...]:
    return (
        NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),
    )


def _items(*numbers: int) -> tuple[NativeExamItem, ...]:
    return tuple(
        make_free_text_item(sequence=number, item_id=f"item_{number:03d}") for number in numbers
    )


def _part(parent_id: str, place: int, children: tuple[int, ...] = ()) -> NativeExamParent:
    return NativeExamParent(
        parent_id=parent_id,
        place=place,
        instruction=_instruction("Do these."),
        item_ids=tuple(f"item_{number:03d}" for number in children),
    )


def _document(
    items: tuple[NativeExamItem, ...],
    parents: tuple[NativeExamParent, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Outline",
        items=items,
        parents=parents,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _assert_round_trip(document: NativeExamDocument) -> None:
    items, parts = outline_items_and_parts(document_outline(document))
    rebuilt = NativeExamDocument(
        document_id=document.document_id,
        revision=document.revision,
        title=document.title,
        header=document.header,
        instructions=document.instructions,
        items=items,
        parents=parts,
        assets=document.assets,
        origin=document.origin,
    )
    assert rebuilt == document


def _part_ids(outline) -> list[str]:
    return [entry.part.parent_id for entry in outline if isinstance(entry, OutlinePart)]


def test_standalone_questions_only_round_trip():
    document = _document(_items(1, 2, 3))
    outline = document_outline(document)

    assert all(isinstance(entry, OutlineQuestion) for entry in outline)
    assert [entry.item.sequence for entry in outline] == [1, 2, 3]
    _assert_round_trip(document)


def test_a_part_in_the_middle_keeps_its_children_and_place():
    document = _document(_items(1, 2, 3, 4), parents=(_part("parent_001", 1, (2, 3)),))
    outline = document_outline(document)

    assert isinstance(outline[0], OutlineQuestion)
    assert isinstance(outline[1], OutlinePart)
    assert [child.sequence for child in outline[1].children] == [2, 3]
    assert isinstance(outline[2], OutlineQuestion)
    assert outline[2].item.sequence == 4
    _assert_round_trip(document)


def test_a_childless_part_at_the_start_keeps_place_zero():
    document = _document(_items(1, 2), parents=(_part("parent_001", 0),))
    outline = document_outline(document)

    assert isinstance(outline[0], OutlinePart)
    assert outline[0].children == ()
    assert isinstance(outline[1], OutlineQuestion)
    _assert_round_trip(document)


def test_a_childless_part_in_the_middle_keeps_its_place():
    document = _document(_items(1, 2), parents=(_part("parent_001", 1),))
    outline = document_outline(document)

    assert isinstance(outline[0], OutlineQuestion)
    assert isinstance(outline[1], OutlinePart)
    assert outline[1].part.place == 1
    assert isinstance(outline[2], OutlineQuestion)
    _assert_round_trip(document)


def test_a_childless_part_at_the_end_keeps_place_len_items():
    document = _document(_items(1, 2), parents=(_part("parent_001", 2),))
    outline = document_outline(document)

    assert [type(entry) for entry in outline] == [OutlineQuestion, OutlineQuestion, OutlinePart]
    assert outline[2].part.place == 2
    _assert_round_trip(document)


def test_two_childless_parts_at_one_place_keep_their_tuple_order():
    document = _document(
        _items(1, 2),
        parents=(_part("parent_001", 1), _part("parent_002", 1)),
    )
    outline = document_outline(document)

    assert _part_ids(outline) == ["parent_001", "parent_002"]
    assert [entry.part.place for entry in outline if isinstance(entry, OutlinePart)] == [1, 1]
    _assert_round_trip(document)


def test_a_childless_part_directly_before_a_part_with_children_stays_first():
    document = _document(
        _items(1, 2),
        parents=(_part("parent_001", 0), _part("parent_002", 0, (1, 2))),
    )
    outline = document_outline(document)

    assert _part_ids(outline) == ["parent_001", "parent_002"]
    assert isinstance(outline[0], OutlinePart)
    assert outline[0].children == ()
    assert isinstance(outline[1], OutlinePart)
    assert [child.sequence for child in outline[1].children] == [1, 2]
    _assert_round_trip(document)


def test_the_writer_renumbers_items_and_sets_each_parts_place_and_children():
    standalone = make_free_text_item(sequence=9, item_id="item_004")
    child_a = make_free_text_item(sequence=9, item_id="item_002")
    child_b = make_free_text_item(sequence=9, item_id="item_003")
    outline = (
        OutlineQuestion(item=standalone),
        OutlinePart(part=_part("parent_001", 7), children=(child_a, child_b)),
    )

    items, parts = outline_items_and_parts(outline)

    assert [item.item_id for item in items] == ["item_004", "item_002", "item_003"]
    assert [item.sequence for item in items] == [1, 2, 3]
    assert parts[0].place == 1
    assert parts[0].item_ids == ("item_002", "item_003")
