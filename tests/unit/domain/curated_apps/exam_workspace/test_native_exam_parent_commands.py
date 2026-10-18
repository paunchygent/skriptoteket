"""Adversarial parent authoring over the real recorded DOCX conversion items."""

import hashlib
from collections.abc import Callable
from functools import partial

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import NativeExamContentTag
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
    parent_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent_commands import (
    add_child,
    create_empty_part,
    create_parent,
    delete_child,
    delete_parent,
    delete_parent_with_children,
    group_items,
    move_item,
    reorder_children,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_ordering_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)

_DELETE_CASES = [
    pytest.param(delete_parent, False, id="heading-only"),
    pytest.param(delete_parent_with_children, False, id="cascade"),
    pytest.param(partial(delete_child, item_id="item_002"), True, id="last-child"),
]


def _childless(parent_id: str, instruction: str, place: int) -> NativeExamParent:
    return NativeExamParent(parent_id=parent_id, place=place, instruction=plain_body(instruction))


def _with_parts(document: NativeExamDocument, *parts: NativeExamParent) -> NativeExamDocument:
    parents = sorted(
        (*document.parents, *parts), key=lambda parent: (parent.place, bool(parent.item_ids))
    )
    return NativeExamDocument.model_validate({**document.model_dump(), "parents": parents})


def _exam() -> NativeExamDocument:
    # Keep a converted mixed-kind parent in place while authoring another parent.
    return recorded_document((parent_over("parent_001", "Existing instruction", 2, 3),))


def _saved_exam(*, single_child: bool = False) -> NativeExamDocument:
    # Recorded conversion items, with explicit test grouping, reopened from the saved JSON shape.
    document = recorded_document(
        (
            parent_over("parent_001", "First instruction", *((2,) if single_child else (2, 3, 4))),
            parent_over("parent_002", "Untouched instruction", 6, 7),
        )
    )
    return parse_native_exam_document(native_exam_document_json_bytes(document))


def _check_structure(document: NativeExamDocument) -> None:
    # Re-enter full validation: model_copy alone does not establish the invariants.
    NativeExamDocument.model_validate(document.model_dump())
    assert [item.sequence for item in document.items] == list(range(1, len(document.items) + 1))


@pytest.mark.parametrize("position", [0, 1, 2])
def test_create_parent_inserts_among_atomic_top_level_units_without_losing_existing_items(
    position: int,
) -> None:
    base = _exam()
    units = [
        ("item_001",),
        ("item_002", "item_003"),
        *((item.item_id,) for item in base.items[3:]),
    ]
    template = next(item for item in base.items if item.kind is NativeExamItemKind.GAP_FILL)

    result = create_parent(
        base, instruction=plain_body("Fyll i rätt form"), child=template, position=position
    )

    new_parent = next(parent for parent in result.parents if parent.parent_id != "parent_001")
    (child_id,) = new_parent.item_ids
    expected_units = [*units[:position], (child_id,), *units[position:]]
    assert [item.item_id for item in result.items] == [i for unit in expected_units for i in unit]
    child = result.item_by_id(child_id)
    assert child.item_id not in {item.item_id for item in base.items}
    assert child.body == template.body
    assert child.points == template.points
    assert child.review.parse_origin is NativeParseOrigin.TEACHER_CREATED
    assert result.parent_of("item_002") == base.parents[0].model_copy(
        update={"place": result.item_by_id("item_002").sequence - 1}
    )
    assert result.revision == base.revision
    _check_structure(result)


@pytest.mark.parametrize(
    ("kind", "exam"),
    [
        (NativeExamItemKind.FREE_TEXT, "svenska_2_grammatik_omprov_variant_1_med_facit"),
        (NativeExamItemKind.MULTIPLE_RESPONSE, "metodprov_vetenskaplig_metod_med_facit"),
        (NativeExamItemKind.SINGLE_CHOICE, "bf26_english_1_unit_test_kap_1_2_med_facit"),
        (NativeExamItemKind.GAP_FILL, "bf26_english_1_unit_test_kap_1_2_med_facit"),
        (NativeExamItemKind.MATCHING, "bf26_english_1_unit_test_kap_1_2_med_facit"),
    ],
)
def test_add_child_accepts_each_existing_kind_and_assigns_identity_without_mutating_the_template(
    kind: NativeExamItemKind,
    exam: str,
) -> None:
    base = _exam()
    template = next(item for item in recorded_items(exam) if item.kind is kind)
    original = template.model_dump()

    result = add_child(base, parent_id="parent_001", child=template, position=1)

    parent = result.parents[0]
    assert parent.item_ids[0] == "item_002"
    assert parent.item_ids[2] == "item_003"
    child = result.item_by_id(parent.item_ids[1])
    assert child.item_id not in {item.item_id for item in base.items}
    assert child.kind is kind
    assert child.body == template.body
    assert child.answer_key == template.answer_key
    assert child.points == template.points
    assert child.review.parse_origin is NativeParseOrigin.TEACHER_CREATED
    assert template.model_dump() == original
    expected_points = sum(base.item_by_id(i).points or 0 for i in base.parents[0].item_ids)
    assert parent_points(result, parent) == expected_points + (template.points or 0)
    _check_structure(result)


def test_reorder_changes_only_the_requested_parent_and_delete_updates_sum() -> None:
    base = recorded_document(
        (
            parent_over("parent_001", "First", 2, 3),
            parent_over("parent_002", "Unchanged", 5, 6),
        )
    )

    reordered = reorder_children(base, parent_id="parent_001", item_ids=("item_003", "item_002"))

    assert [item.item_id for item in reordered.items] == [
        "item_001",
        "item_003",
        "item_002",
        *(item.item_id for item in base.items[3:]),
    ]
    assert reordered.parents[1] == base.parents[1]
    assert reordered.items[3:] == base.items[3:]
    assert parent_points(reordered, reordered.parents[0]) == parent_points(base, base.parents[0])
    _check_structure(reordered)

    deleted = delete_child(reordered, parent_id="parent_001", item_id="item_003")

    assert deleted.parents[0].item_ids == ("item_002",)
    assert {item.item_id for item in deleted.items} == {
        item.item_id for item in base.items if item.item_id != "item_003"
    }
    assert parent_points(deleted, deleted.parents[0]) == base.item_by_id("item_002").points
    _check_structure(deleted)
    last_child_deleted = delete_child(deleted, parent_id="parent_001", item_id="item_002")

    kept = last_child_deleted.parents[0]
    assert kept.parent_id == "parent_001"
    assert kept.item_ids == ()
    assert kept.place == 1, "The empty part stays where its first question stood (G8)"
    assert kept.instruction == base.parents[0].instruction
    assert last_child_deleted.parents[1] == base.parents[1].model_copy(
        update={"place": last_child_deleted.item_by_id(base.parents[1].item_ids[0]).sequence - 1}
    )
    assert last_child_deleted.parent_of("item_002") is None
    assert [item.item_id for item in last_child_deleted.items] == [
        item.item_id for item in base.items if item.item_id not in {"item_002", "item_003"}
    ]
    _check_structure(last_child_deleted)


@pytest.mark.parametrize(
    "item_ids",
    [
        ("item_002",),
        ("item_002", "item_002"),
        ("item_002", "item_001"),
        ("item_002", "item_003", "item_004"),
    ],
    ids=["missing-child", "duplicate-child", "standalone-substituted", "extra-child"],
)
def test_reorder_requires_the_exact_permutation_not_merely_known_item_ids(
    item_ids: tuple[str, ...],
) -> None:
    base = _exam()
    with pytest.raises(DomainError):
        reorder_children(base, parent_id="parent_001", item_ids=item_ids)


@pytest.mark.parametrize("single_child", [False, True], ids=["multiple-children", "last-child"])
@pytest.mark.parametrize("item_id", ["item_001", "item_006", "item_999", "item_002 "])
def test_delete_cannot_take_a_standalone_another_parents_child_or_missing_id(
    item_id: str, single_child: bool
) -> None:
    base = _saved_exam(single_child=single_child)
    original = native_exam_document_json_bytes(base)

    with pytest.raises(DomainError) as error:
        delete_child(base, parent_id="parent_001", item_id=item_id)

    assert error.value.code is ErrorCode.NOT_FOUND
    assert error.value.details == {"parent_id": "parent_001", "item_id": item_id}
    assert native_exam_document_json_bytes(base) == original


@pytest.mark.parametrize("shared", [False, True], ids=["last-reference", "shared-instruction"])
def test_deleting_an_imaged_child_prunes_only_assets_with_no_remaining_reference(
    shared: bool,
) -> None:
    base = _exam()
    asset_id = "asset_00000000000000a1"
    paragraph = NativeParagraph(
        heading_level=None, segments=(NativeAssetSegment(asset_id=asset_id),)
    )
    imaged = base.item_by_id("item_002").model_copy(
        update={"body": (*base.item_by_id("item_002").body, paragraph)}
    )
    asset = NativeExamAsset(
        asset_id=asset_id,
        sha256=hashlib.sha256(b"recorded-image-bytes").hexdigest(),
        media_type="image/png",
        byte_length=len(b"recorded-image-bytes"),
    )
    parent = base.parents[0]
    if shared:
        parent = parent.model_copy(update={"instruction": (*parent.instruction, paragraph)})
    base = NativeExamDocument.model_validate(
        {
            **base.model_dump(),
            "items": tuple(imaged if i.item_id == imaged.item_id else i for i in base.items),
            "parents": (parent,),
            "assets": (asset,),
        }
    )

    result = delete_child(base, parent_id="parent_001", item_id="item_002")

    assert result.assets == ((asset,) if shared else ())
    _check_structure(result)


@pytest.mark.parametrize("origin", ["suggested", "teacher"])
def test_child_delete_prunes_only_removed_citations_and_keeps_selected_tag(origin: str) -> None:
    base = _exam()
    tag = NativeExamContentTag.model_validate(
        {
            "id": "course:content",
            "text": "Lärarens valda innehåll",
            "origin": origin,
            "question_ids": ("item_002", "item_003", "item_001"),
        }
    )
    orphaned = tag.model_copy(update={"id": "course:only-deleted", "question_ids": ("item_002",)})
    base = NativeExamDocument.model_validate(
        dict(
            base.model_dump(),
            header=base.header.model_copy(
                update={
                    "course": ExamCourseChoice(key="course", name="Course"),
                    "tags": (tag, orphaned),
                }
            ),
        )
    )
    reordered = reorder_children(base, parent_id="parent_001", item_ids=("item_003", "item_002"))
    assert reordered.header == base.header

    result = delete_child(reordered, parent_id="parent_001", item_id="item_002")

    assert result.header.tags == (
        tag.model_copy(update={"question_ids": ("item_003", "item_001")}),
        orphaned.model_copy(update={"question_ids": ()}),
    )
    _check_structure(result)
    assert base.header.tags == (tag, orphaned), "The immutable source keeps its citations"


def test_delete_heading_keeps_saved_items_at_their_positions_with_unchanged_points() -> None:
    base = _saved_exam()
    original = native_exam_document_json_bytes(base)
    parent = base.parents[0]
    assert parent.item_ids == ("item_002", "item_003", "item_004")
    assert base.parent_of("item_001") is None
    assert base.parent_of("item_005") is None

    result = delete_parent(base, parent_id=parent.parent_id)

    assert result.items == base.items, "Every field, including sequence, content and points, stays"
    assert all(result.parent_of(item_id) is None for item_id in parent.item_ids)
    assert result.parents == (base.parents[1],)
    assert result.header == base.header
    assert result.document_id == base.document_id
    assert result.revision == base.revision
    assert result.title == base.title
    assert result.origin == base.origin
    assert native_exam_document_json_bytes(base) == original
    _check_structure(result)


def test_cascade_removes_exactly_the_three_children_and_renumbers_all_survivors() -> None:
    base = _saved_exam()
    original = native_exam_document_json_bytes(base)

    result = delete_parent_with_children(base, parent_id="parent_001")

    survivors = [
        item for item in base.items if item.item_id not in {"item_002", "item_003", "item_004"}
    ]
    assert [item.model_dump() for item in result.items] == [
        dict(item.model_dump(), sequence=sequence)
        for sequence, item in enumerate(survivors, start=1)
    ]
    assert result.parents == (
        base.parents[1].model_copy(
            update={"place": result.item_by_id(base.parents[1].item_ids[0]).sequence - 1}
        ),
    )
    assert [result.item_by_id(item_id).sequence for item_id in result.parents[0].item_ids] == [3, 4]
    assert parent_points(result, result.parents[0]) == parent_points(base, base.parents[1])
    assert result.document_id == base.document_id
    assert result.revision == base.revision
    assert result.header == base.header
    assert result.origin == base.origin
    assert native_exam_document_json_bytes(base) == original
    _check_structure(result)


def test_deleting_the_last_child_keeps_its_parent_as_a_childless_instruction_block() -> None:
    base = _saved_exam(single_child=True)
    original = native_exam_document_json_bytes(base)

    result = delete_child(base, parent_id="parent_001", item_id="item_002")

    kept = next(parent for parent in result.parents if parent.parent_id == "parent_001")
    assert kept.item_ids == ()
    assert kept.place == 1
    assert kept.instruction == base.parents[0].instruction
    assert next(parent for parent in result.parents if parent.parent_id == "parent_002") == (
        base.parents[1].model_copy(
            update={"place": result.item_by_id(base.parents[1].item_ids[0]).sequence - 1}
        )
    )
    assert [item.model_dump() for item in result.items] == [
        dict(item.model_dump(), sequence=sequence)
        for sequence, item in enumerate(
            (item for item in base.items if item.item_id != "item_002"), start=1
        )
    ]
    assert result.item_by_id("item_003").sequence == 2
    assert result.parent_of("item_003") is None
    assert native_exam_document_json_bytes(base) == original
    _check_structure(result)


@pytest.mark.parametrize("command", [delete_parent, delete_parent_with_children, delete_child])
@pytest.mark.parametrize("parent_id", ["parent_999", "item_002", "parent_01", "parent_001 "])
def test_parent_deletes_require_exact_existing_parent_identity(
    command: Callable[..., NativeExamDocument], parent_id: str
) -> None:
    base = _saved_exam()
    original = native_exam_document_json_bytes(base)
    extra = {"item_id": "item_002"} if command is delete_child else {}

    with pytest.raises(DomainError) as error:
        command(base, parent_id=parent_id, **extra)

    assert error.value.code is ErrorCode.NOT_FOUND
    assert error.value.details == {"parent_id": parent_id}
    assert native_exam_document_json_bytes(base) == original


@pytest.mark.parametrize(("command", "single_child"), _DELETE_CASES)
@pytest.mark.parametrize("origin", ["suggested", "teacher"])
def test_parent_deletes_keep_selected_tags_and_prune_only_deleted_question_citations(
    command: Callable[..., NativeExamDocument], single_child: bool, origin: str
) -> None:
    base = _saved_exam(single_child=single_child)
    tag = NativeExamContentTag.model_validate(
        {
            "id": "course:shared",
            "text": "Selected content",
            "origin": origin,
            "question_ids": ("item_002", "item_003", "item_001", "item_006"),
        }
    )
    only_deleted = tag.model_copy(
        update={"id": "course:only-deleted", "question_ids": ("item_002",)}
    )
    base = base.model_copy(
        update={
            "header": base.header.model_copy(
                update={
                    "course": ExamCourseChoice(key="course", name="Course"),
                    "tags": (tag, only_deleted),
                }
            )
        }
    )
    base = parse_native_exam_document(native_exam_document_json_bytes(base))
    original = native_exam_document_json_bytes(base)

    result = command(base, parent_id="parent_001")

    expected_ids = (
        tag.question_ids
        if command is delete_parent
        else (("item_003", "item_001", "item_006") if single_child else ("item_001", "item_006"))
    )
    assert result.header == base.header.model_copy(
        update={
            "tags": (
                tag.model_copy(update={"question_ids": expected_ids}),
                only_deleted.model_copy(
                    update={
                        "question_ids": only_deleted.question_ids
                        if command is delete_parent
                        else ()
                    }
                ),
            )
        }
    )
    assert native_exam_document_json_bytes(base) == original
    _check_structure(result)


@pytest.mark.parametrize(
    ("command", "child_count"),
    [(delete_parent_with_children, 3), (partial(delete_child, item_id="item_001"), 1)],
)
def test_deletes_that_would_empty_the_document_raise_named_question_required_error(
    command: Callable[..., NativeExamDocument],
    child_count: int,
) -> None:
    base = recorded_document(
        (parent_over("parent_001", "Only instruction", *range(1, child_count + 1)),),
        items=recorded_items()[:child_count],
    )
    original = native_exam_document_json_bytes(base)

    with pytest.raises(DomainError) as error:
        command(base, parent_id="parent_001")

    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert error.value.message == "Provet måste ha minst en fråga."
    assert error.value.details == {"reason": "exam_requires_question", "parent_id": "parent_001"}
    assert native_exam_document_json_bytes(base) == original


def test_deleting_the_only_heading_still_keeps_the_document_nonempty() -> None:
    base = recorded_document(
        (parent_over("parent_001", "Only instruction", 1),), items=recorded_items()[:1]
    )

    result = delete_parent(base, parent_id="parent_001")

    assert result.parents == ()
    assert result.items == base.items
    _check_structure(result)


def test_create_parent_counts_a_childless_part_as_a_top_level_position() -> None:
    base = _with_parts(_exam(), _childless("parent_002", "Instruktionsblock", 4))
    template = next(item for item in base.items if item.kind is NativeExamItemKind.GAP_FILL)

    result = create_parent(base, instruction=plain_body("Ny del"), child=template, position=3)

    new_parent = next(
        parent for parent in result.parents if parent.parent_id not in {"parent_001", "parent_002"}
    )
    (child_id,) = new_parent.item_ids
    assert [item.item_id for item in result.items[:6]] == [
        "item_001",
        "item_002",
        "item_003",
        "item_004",
        child_id,
        "item_005",
    ]
    assert new_parent.place == 4
    preserved = next(parent for parent in result.parents if parent.parent_id == "parent_002")
    assert preserved.item_ids == ()
    assert preserved.place == 5, "The inserted question now stands before the block"
    assert result.parents.index(preserved) > result.parents.index(new_parent)
    _check_structure(result)


def test_delete_parent_leaves_children_standalone_at_the_parts_place() -> None:
    base = _with_parts(_saved_exam(), _childless("parent_003", "Instruktionsblock", 4))
    block = next(parent for parent in base.parents if parent.parent_id == "parent_003")

    result = delete_parent(base, parent_id="parent_001")

    assert all(
        result.parent_of(item_id) is None for item_id in ("item_002", "item_003", "item_004")
    )
    assert [
        result.item_by_id(item_id).sequence for item_id in ("item_002", "item_003", "item_004")
    ] == [
        2,
        3,
        4,
    ]
    assert next(parent for parent in result.parents if parent.parent_id == "parent_003") == block
    _check_structure(result)


def test_reorder_children_and_add_child_keep_a_childless_part_at_its_place() -> None:
    base = _with_parts(_exam(), _childless("parent_002", "Instruktionsblock", 5))
    block = next(parent for parent in base.parents if parent.parent_id == "parent_002")
    template = next(item for item in base.items if item.kind is NativeExamItemKind.GAP_FILL)

    reordered = reorder_children(base, parent_id="parent_001", item_ids=("item_003", "item_002"))
    assert next(parent for parent in reordered.parents if parent.parent_id == "parent_002") == block

    added = add_child(reordered, parent_id="parent_001", child=template, position=1)
    preserved = next(parent for parent in added.parents if parent.parent_id == "parent_002")
    assert preserved.item_ids == ()
    assert preserved.place == block.place + 1
    assert preserved.place == added.item_by_id("item_005").sequence
    _check_structure(added)


def _six() -> NativeExamDocument:
    return recorded_document(items=recorded_items()[:6])


def test_group_non_adjacent_questions_takes_the_first_place_and_keeps_the_rest_in_order() -> None:
    base = _six()
    original = native_exam_document_json_bytes(base)

    result, parent_id = group_items(base, item_ids=("item_002", "item_005"))

    assert [item.item_id for item in result.items] == [
        "item_001",
        "item_002",
        "item_005",
        "item_003",
        "item_004",
        "item_006",
    ]
    assert [item.sequence for item in result.items] == [1, 2, 3, 4, 5, 6]
    part = next(parent for parent in result.parents if parent.parent_id == parent_id)
    assert part.item_ids == ("item_002", "item_005")
    assert part.place == 1, "The part takes the place of the earliest marked question (G10)"
    assert part.instruction == (), "A new part starts with an empty instruction (G4)"
    assert [result.item_by_id(item_id).sequence for item_id in part.item_ids] == [2, 3]
    assert native_exam_document_json_bytes(base) == original
    _check_structure(result)


def test_group_one_question_makes_a_part_holding_exactly_that_question() -> None:
    base = _six()

    result, parent_id = group_items(base, item_ids=("item_002",))

    part = next(parent for parent in result.parents if parent.parent_id == parent_id)
    assert part.item_ids == ("item_002",)
    assert part.place == 1
    assert [item.item_id for item in result.items] == [
        "item_001",
        "item_002",
        "item_003",
        "item_004",
        "item_005",
        "item_006",
    ]
    _check_structure(result)


def test_group_refuses_empty_duplicate_and_unknown_items_with_named_reasons() -> None:
    base = _six()

    with pytest.raises(DomainError) as empty:
        group_items(base, item_ids=())
    assert empty.value.code is ErrorCode.VALIDATION_ERROR
    assert empty.value.message == "Markera minst en fråga."
    assert empty.value.details == {"reason": "no_items"}

    with pytest.raises(DomainError) as duplicate:
        group_items(base, item_ids=("item_002", "item_002"))
    assert duplicate.value.details == {"reason": "duplicate_items"}

    with pytest.raises(DomainError) as unknown:
        group_items(base, item_ids=("item_999",))
    assert unknown.value.code is ErrorCode.NOT_FOUND
    assert unknown.value.details == {"item_id": "item_999"}


def test_group_refuses_an_existing_child_and_an_ordering_question() -> None:
    with pytest.raises(DomainError) as child:
        group_items(_exam(), item_ids=("item_002",))
    assert child.value.code is ErrorCode.VALIDATION_ERROR
    assert child.value.message == "Frågan ligger redan i en del. Flytta den med Flytta till…"
    assert child.value.details == {"reason": "item_in_part", "item_id": "item_002"}

    ordering = make_document(
        make_free_text_item(sequence=1, item_id="item_001"),
        make_ordering_item(sequence=2, item_id="item_002"),
    )
    with pytest.raises(DomainError) as ordering_error:
        group_items(ordering, item_ids=("item_002",))
    assert ordering_error.value.details == {
        "reason": "ordering_inside_parent",
        "item_id": "item_002",
    }


def test_move_standalone_into_a_part_lands_last_and_keeps_the_parts_place() -> None:
    base = _exam()

    result = move_item(base, item_id="item_001", target_parent_id="parent_001")

    part = result.parents[0]
    assert part.parent_id == "parent_001"
    assert part.item_ids == ("item_002", "item_003", "item_001")
    assert part.place == 0
    assert [result.item_by_id(item_id).sequence for item_id in part.item_ids] == [1, 2, 3]
    assert result.item_by_id("item_001").sequence == 3
    _check_structure(result)


def test_move_between_parts_lands_last_in_the_target_and_the_source_keeps_its_place() -> None:
    base = recorded_document(
        (parent_over("parent_001", "A", 2, 3), parent_over("parent_002", "B", 5, 6))
    )

    result = move_item(base, item_id="item_002", target_parent_id="parent_002")

    source = next(parent for parent in result.parents if parent.parent_id == "parent_001")
    target = next(parent for parent in result.parents if parent.parent_id == "parent_002")
    assert source.item_ids == ("item_003",)
    assert source.place == 1
    assert target.item_ids == ("item_005", "item_006", "item_002")
    assert result.item_by_id("item_002").sequence == target.place + 3
    _check_structure(result)

    emptied = move_item(result, item_id="item_003", target_parent_id="parent_002")

    source = next(parent for parent in emptied.parents if parent.parent_id == "parent_001")
    target = next(parent for parent in emptied.parents if parent.parent_id == "parent_002")
    assert source.item_ids == (), "A part left with no questions stays (G8)"
    assert source.place == 1
    assert target.item_ids[-1] == "item_003"
    _check_structure(emptied)


def test_move_out_lands_directly_after_the_part_it_left() -> None:
    base = _exam()

    result = move_item(base, item_id="item_002", target_parent_id=None)

    part = result.parents[0]
    assert part.item_ids == ("item_003",)
    assert result.item_by_id("item_002").sequence == part.place + len(part.item_ids) + 1
    assert [item.item_id for item in result.items][:4] == [
        "item_001",
        "item_003",
        "item_002",
        "item_004",
    ]
    _check_structure(result)


def test_move_out_of_a_one_question_part_leaves_a_childless_part_before_the_question() -> None:
    base = recorded_document((parent_over("parent_001", "A", 2),))

    result = move_item(base, item_id="item_002", target_parent_id=None)

    part = result.parents[0]
    assert part.item_ids == ()
    assert part.place == 1
    assert result.item_by_id("item_002").sequence == 2
    _check_structure(result)


def test_move_refuses_unknown_ids_the_same_part_and_ordering_into_a_part() -> None:
    base = _exam()

    with pytest.raises(DomainError) as unknown_part:
        move_item(base, item_id="item_002", target_parent_id="parent_999")
    assert unknown_part.value.code is ErrorCode.NOT_FOUND
    assert unknown_part.value.details == {"parent_id": "parent_999"}

    with pytest.raises(DomainError) as same_part:
        move_item(base, item_id="item_002", target_parent_id="parent_001")
    assert same_part.value.details == {
        "reason": "already_in_part",
        "parent_id": "parent_001",
        "item_id": "item_002",
    }

    with pytest.raises(DomainError) as standalone:
        move_item(base, item_id="item_001", target_parent_id=None)
    assert standalone.value.details == {"reason": "already_standalone", "item_id": "item_001"}

    with pytest.raises(DomainError) as unknown_item:
        move_item(base, item_id="item_999", target_parent_id=None)
    assert unknown_item.value.code is ErrorCode.NOT_FOUND
    assert unknown_item.value.details == {"item_id": "item_999"}

    ordering = _with_parts(
        make_document(
            make_free_text_item(sequence=1, item_id="item_001"),
            make_ordering_item(sequence=2, item_id="item_002"),
        ),
        _childless("parent_001", "Block", 1),
    )
    with pytest.raises(DomainError) as ordering_error:
        move_item(ordering, item_id="item_002", target_parent_id="parent_001")
    assert ordering_error.value.details == {
        "reason": "ordering_inside_parent",
        "item_id": "item_002",
    }


@pytest.mark.parametrize("position", [0, 3, 6])
def test_create_empty_part_inserts_a_childless_instruction_block_at_the_position(
    position: int,
) -> None:
    base = _six()

    result, parent_id = create_empty_part(base, position=position)

    part = next(parent for parent in result.parents if parent.parent_id == parent_id)
    assert part.item_ids == ()
    assert part.instruction == ()
    assert part.place == position
    assert [item.item_id for item in result.items] == [
        "item_001",
        "item_002",
        "item_003",
        "item_004",
        "item_005",
        "item_006",
    ]
    _check_structure(result)


def test_create_empty_part_refuses_a_position_beyond_the_outline() -> None:
    with pytest.raises(DomainError) as error:
        create_empty_part(_six(), position=7)

    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert error.value.message == "Positionen finns inte."
    assert error.value.details == {"position": 7}


def test_a_childless_part_is_never_lost_by_group_move_empty_or_delete() -> None:
    base = _with_parts(_six(), _childless("parent_001", "Instruktionsblock", 3))

    grouped, new_part_id = group_items(base, item_ids=("item_002", "item_005"))
    assert next(p for p in grouped.parents if p.parent_id == "parent_001").item_ids == ()

    moved = move_item(grouped, item_id="item_006", target_parent_id=new_part_id)
    assert next(p for p in moved.parents if p.parent_id == "parent_001").item_ids == ()

    emptied, _ = create_empty_part(moved, position=0)
    surviving = next(p for p in emptied.parents if p.parent_id == "parent_001")
    assert surviving.item_ids == ()
    assert surviving.place == 5

    deleted = delete_child(emptied, parent_id=new_part_id, item_id="item_002")
    surviving = next(p for p in deleted.parents if p.parent_id == "parent_001")
    assert surviving.item_ids == ()
    assert surviving.place == 4
    target = next(p for p in deleted.parents if p.parent_id == new_part_id)
    assert target.item_ids == ("item_005", "item_006")
    _check_structure(deleted)
