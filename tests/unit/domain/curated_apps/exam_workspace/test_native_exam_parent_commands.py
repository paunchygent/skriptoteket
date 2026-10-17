"""Adversarial parent authoring over the real recorded DOCX conversion items."""

import hashlib

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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import parent_points
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent_commands import (
    add_child,
    create_parent,
    delete_child,
    reorder_children,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import DomainError
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
    recorded_items,
)


def _exam() -> NativeExamDocument:
    # Keep a converted mixed-kind parent in place while authoring another parent.
    return recorded_document((parent_over("parent_001", "Existing instruction", 2, 3),))


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
    assert result.parent_of("item_002") == base.parents[0]
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
    with pytest.raises(DomainError) as error:
        delete_child(deleted, parent_id="parent_001", item_id="item_002")
    assert error.value.details is not None
    assert error.value.details["reason"] == "parent_requires_child"


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


def test_delete_cannot_take_a_standalone_or_another_parents_child() -> None:
    base = recorded_document(
        (parent_over("parent_001", "First", 2, 3), parent_over("parent_002", "Second", 5, 6))
    )
    for item_id in ("item_001", "item_005"):
        with pytest.raises(DomainError):
            delete_child(base, parent_id="parent_001", item_id=item_id)


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
