"""QTI import mapping: parents and information parts.

Split from test_qti_import_mapping.py by tested responsibility. Covers parent
places, kept children, and information items that become childless parts.
"""

from dataclasses import replace
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    validate_parent_structure,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import import (
    build_native_exam_from_qti,
)
from tests.unit.domain.curated_apps.exam_workspace.qti_import_mapping_support import (
    _SOURCE_SHA,
    _information_qti_item,
    _qti_item,
)


def test_an_ordering_child_in_a_part_imports_at_one_point_without_a_note() -> None:
    ordering_child = replace(
        _qti_item(
            ExamNetQtiInteractionType.ORDERING,
            sequence=1,
            opening="Sortera stegen",
            choices=(
                ExamNetQtiChoice(identifier="s2", text="Argument"),
                ExamNetQtiChoice(identifier="s1", text="Tes"),
            ),
            correct_choice_identifiers=("s1", "s2"),
        ),
        max_score=3,
    )
    text_child = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=2, opening="Resonera")
    parent = _qti_item(
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        sequence=3,
        opening="Deluppgifter",
        children=(ordering_child, text_child),
    )

    container = build_native_exam_from_qti(
        items=(parent,),
        document_id=uuid4(),
        source_filename="foralder.zip",
        source_sha256=_SOURCE_SHA,
    )

    document = container.document
    assert [item.kind for item in document.items] == [
        NativeExamItemKind.ORDERING,
        NativeExamItemKind.FREE_TEXT,
    ]
    ordering = document.items[0]
    assert ordering.points == 1
    assert ordering.points_estimated is False
    assert document.parents[0].place == 0
    assert document.parents[0].item_ids == ("item_001", "item_002")
    assert container.notes == ()


def test_two_parents_after_standalone_items_carry_their_own_places() -> None:
    """Each imported parent stores the count of native items before its first child."""

    def free_text(sequence: int, opening: str) -> ExamNetQtiItem:
        return _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=sequence, opening=opening)

    def parent(sequence: int, opening: str, first: int, second: int) -> ExamNetQtiItem:
        return _qti_item(
            ExamNetQtiInteractionType.SINGLE_CHOICE,
            sequence=sequence,
            opening=opening,
            children=(
                free_text(first, f"Deluppgift {first}"),
                free_text(second, f"Deluppgift {second}"),
            ),
        )

    container = build_native_exam_from_qti(
        items=(
            free_text(1, "Fristående först"),
            parent(2, "Första delen", 1, 2),
            free_text(3, "Fristående mellan"),
            parent(4, "Andra delen", 3, 4),
        ),
        document_id=uuid4(),
        source_filename="delar.zip",
        source_sha256=_SOURCE_SHA,
    )

    document = container.document
    assert [item.sequence for item in document.items] == [1, 2, 3, 4, 5, 6]
    first_place = len(document.items[:1])
    second_place = len(document.items[:4])
    assert [parent.place for parent in document.parents] == [first_place, second_place]
    assert document.parents[0].item_ids == ("item_002", "item_003")
    assert document.parents[1].item_ids == ("item_005", "item_006")
    validate_parent_structure(document.parents, document.items)


def test_a_parent_with_a_skipped_first_child_counts_only_kept_items() -> None:
    """A skipped first child never shifts the parent's place or its kept children."""

    skipped = _qti_item(
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        sequence=1,
        opening="Bara ett alternativ",
        choices=(ExamNetQtiChoice(identifier="c1", text="Ett"),),
        correct_choice_identifiers=("c1",),
    )
    kept_first = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=2, opening="Första kept")
    kept_second = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=3, opening="Andra kept")
    stem = _qti_item(
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        sequence=2,
        opening="Deluppgifter",
        children=(skipped, kept_first, kept_second),
    )
    leading = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=1, opening="Fristående först")

    container = build_native_exam_from_qti(
        items=(leading, stem),
        document_id=uuid4(),
        source_filename="hoppad-forst.zip",
        source_sha256=_SOURCE_SHA,
    )

    document = container.document
    assert [item.sequence for item in document.items] == [1, 2, 3]
    (imported_parent,) = document.parents
    assert imported_parent.place == len(document.items[:1])
    assert imported_parent.item_ids == ("item_002", "item_003")
    assert document.items[1].sequence == imported_parent.place + 1
    validate_parent_structure(document.parents, document.items)
    assert container.notes == (
        "Fråga 1 – Bara ett alternativ: frågetypen stöds inte och importerades inte.",
    )


def test_information_items_become_childless_parts_at_their_places() -> None:
    """A part with no questions keeps its place between and after the questions."""

    def free_text(sequence: int, opening: str) -> ExamNetQtiItem:
        return _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=sequence, opening=opening)

    parent = _qti_item(
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        sequence=3,
        opening="Deluppgifter",
        children=(
            free_text(1, "Deluppgift ett"),
            free_text(2, "Deluppgift två"),
        ),
    )

    container = build_native_exam_from_qti(
        items=(
            free_text(1, "Fristående först"),
            _information_qti_item(2, ("Läs texten först.",)),
            parent,
            _information_qti_item(4, ("Efter alla frågor.",)),
        ),
        document_id=uuid4(),
        source_filename="informationsdelar.zip",
        source_sha256=_SOURCE_SHA,
    )

    document = container.document
    assert [item.sequence for item in document.items] == [1, 2, 3]
    assert [parent.parent_id for parent in document.parents] == [
        "parent_001",
        "parent_002",
        "parent_003",
    ]
    assert [parent.place for parent in document.parents] == [1, 1, 3]
    assert document.parents[0].place == len(document.items[:1])
    assert document.parents[2].place == len(document.items[:3])
    assert document.parents[0].item_ids == ()
    assert document.parents[1].item_ids == ("item_002", "item_003")
    assert document.parents[2].item_ids == ()
    from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
        NativeTextSegment,
    )
    from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text

    assert body_plain_text(document.parents[0].instruction) == "Läs texten först."
    assert body_plain_text(document.parents[2].instruction) == "Efter alla frågor."
    assert all(
        isinstance(segment, NativeTextSegment)
        for parent in (document.parents[0], document.parents[2])
        for paragraph in parent.instruction
        for segment in paragraph.segments
    )
    assert sum(item.points for item in document.items if item.points is not None) == 3
    assert container.notes == ()
    validate_parent_structure(document.parents, document.items)
