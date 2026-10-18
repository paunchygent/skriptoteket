"""Conversion merge over parts: parent membership, childless blocks and expanded children."""

from __future__ import annotations

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionMerge,
    ConversionProgress,
    first_conversion,
    merge_conversion,
    target_from_update,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_merge_test_support import (  # noqa: E501
    _teacher_save,
    _texts,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    body,
    choice,
    conversion_update,
    placeholder,
)


def _block(parent_id: str, place: int, text: str = "Lärarens instruktion") -> NativeExamParent:
    """A teacher-made instruction block: a part with no questions."""
    return NativeExamParent(parent_id=parent_id, place=place, instruction=body(text))


_FINAL_UNITS = [
    ("q1", [choice("p1", "Fråga ett")]),
    ("q2", [choice("p2", "Fråga två")]),
    ("q3", [choice("p3", "Fråga tre")]),
]


def _final_with_parent(head: NativeExamDocument, progress: ConversionProgress) -> ConversionMerge:
    return merge_conversion(
        head=head,
        progress=progress,
        target=target_from_update(
            conversion_update(_FINAL_UNITS, pending=(), parents=(("P", ("q1", "q2", "q3")),))
        ),
    )


def _instruction_of(document: NativeExamDocument) -> dict[str, tuple[str, ...] | None]:
    return {
        item.item_id: (
            body_text_lines(parent.instruction)
            if (parent := document.parent_of(item.item_id))
            else None
        )
        for item in document.items
    }


def test_final_parents_map_to_saved_ids(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    merged = _final_with_parent(head, progress)
    assert [p.item_ids for p in merged.document.parents] == [("item_001", "item_002", "item_003")]


def test_teacher_edited_converted_child_stays_under_the_final_parent(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    edited = head.items[0].model_copy(update={"body": body("Lärarens fråga ett")})
    teacher_head = _teacher_save(head, items=(edited, *head.items[1:]))

    merged = _final_with_parent(teacher_head, progress)

    assert _texts(merged.document)[0] == "Lärarens fråga ett"
    assert [p.item_ids for p in merged.document.parents] == [("item_001", "item_002", "item_003")]
    assert merged.document.parent_of("item_001") is not None


def test_teacher_deleted_converted_sibling_leaves_the_rest_under_the_instruction(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    # q2 converts first; the teacher then deletes the converted q2.
    q2_ready = merge_conversion(
        head=head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", [choice("p2", "Fråga två")]),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q3",),
            )
        ),
    )
    items = q2_ready.document.items
    teacher_head = _teacher_save(
        q2_ready.document, items=(items[0], items[2].model_copy(update={"sequence": 2}))
    )

    merged = _final_with_parent(teacher_head, q2_ready.progress)

    assert _texts(merged.document) == ["Fråga ett", "Fråga tre"]
    assert [p.item_ids for p in merged.document.parents] == [("item_001", "item_003")]
    assert set(_instruction_of(merged.document).values()) == {("Välj rätt svar.",)}


def test_teacher_retyped_first_child_keeps_it_under_the_same_parent(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    retyped = placeholder("p1", "Lärarens fritextfråga").model_copy(
        update={"item_id": head.items[0].item_id, "sequence": 1}
    )
    teacher_head = _teacher_save(head, items=(retyped, *head.items[1:]))

    merged = _final_with_parent(teacher_head, progress)

    assert merged.document.items[0].kind is NativeExamItemKind.FREE_TEXT
    assert [p.item_ids for p in merged.document.parents] == [("item_001", "item_002", "item_003")]
    assert set(_instruction_of(merged.document).values()) == {("Välj rätt svar.",)}


def test_teacher_childless_part_survives_a_merge_that_replaces_the_first_question(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    block = _block("parent_001", 2)
    teacher_head = _teacher_save(head, parents=(block,))

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett igen")]),
                    ("q2", [placeholder("p2", "Källtext två")]),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q2", "q3"),
            )
        ),
    )

    assert _texts(merged.document) == ["Fråga ett igen", "Källtext två", "Källtext tre"]
    assert merged.document.parents == (block,)
    assert merged.document.parents[0].place == 2
    assert merged.document.parents[0].item_ids == ()


def test_childless_part_moves_back_to_the_nearest_surviving_earlier_question(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    block = _block("parent_001", 2)
    teacher_head = _teacher_save(head, parents=(block,))

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", []),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q2", "q3"),
            )
        ),
    )

    assert [item.item_id for item in merged.document.items] == ["item_001", "item_003"]
    (parent,) = merged.document.parents
    assert parent.item_ids == ()
    assert parent.place == 1, "The anchor is gone, so the block follows item_001"


def test_childless_part_at_place_zero_stays_at_zero(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    block = _block("parent_001", 0)
    teacher_head = _teacher_save(head, parents=(block,))

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett igen")]),
                    ("q2", [placeholder("p2", "Källtext två")]),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q2", "q3"),
            )
        ),
    )

    assert merged.document.parents == (block,)
    assert merged.document.parents[0].place == 0


def _q2_q3_part() -> tuple[NativeExamDocument, ConversionProgress]:
    merged = first_conversion(
        update=conversion_update(
            [
                ("q1", [choice("p1", "Fråga ett")]),
                ("q2", [placeholder("p2", "Källtext två")]),
                ("q3", [placeholder("p3", "Källtext tre")]),
            ],
            pending=("q2", "q3"),
            parents=(("section", ("q2", "q3")),),
        ),
        progress=ConversionProgress.from_question_ids(["q1", "q2", "q3"]),
    )
    return merged.document, merged.progress


def _teacher_edited_part(document: NativeExamDocument) -> NativeExamDocument:
    (part,) = document.parents
    return _teacher_save(
        document,
        parents=(part.model_copy(update={"instruction": body("Lärarens instruktion")}),),
    )


def test_an_expanded_child_stays_in_its_part_in_its_slot() -> None:
    first_merge = first_conversion(
        update=conversion_update(
            [
                ("q1", [choice("p1", "Fråga ett")]),
                ("q2", [placeholder("p2", "Källtext två")]),
                ("q3", [placeholder("p3", "Källtext tre")]),
            ],
            pending=("q2", "q3"),
            parents=(("section", ("q2", "q3")),),
        ),
        progress=ConversionProgress.from_question_ids(["q1", "q2", "q3"]),
    )
    # The teacher's block keeps the saved parents; the expanded q2 stays in the part's slot.
    head = _teacher_save(
        first_merge.document,
        parents=(_block("parent_002", 0), *first_merge.document.parents),
    )

    merged = merge_conversion(
        head=head,
        progress=first_merge.progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", [choice("p2", "Fråga två a"), choice("p2b", "Fråga två b")]),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q3",),
            )
        ),
    )

    assert [item.item_id for item in merged.document.items] == [
        "item_001",
        "item_002",
        "item_1001",
        "item_003",
    ]
    assert [item.sequence for item in merged.document.items] == [1, 2, 3, 4]
    parents = merged.document.parents
    assert [parent.parent_id for parent in parents] == ["parent_002", "parent_001"]
    assert parents[0].item_ids == ()
    assert parents[0].place == 0
    assert parents[1].item_ids == ("item_002", "item_1001", "item_003")
    assert parents[1].place == 1


def test_an_expanded_first_child_keeps_the_teachers_instruction() -> None:
    document, progress = _q2_q3_part()
    teacher_head = _teacher_edited_part(document)

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", [choice("p2", "Fråga två a"), choice("p2b", "Fråga två b")]),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=(),
            )
        ),
    )

    (parent,) = merged.document.parents
    assert parent.item_ids == ("item_002", "item_1001", "item_003")
    assert body_text_lines(parent.instruction) == ("Lärarens instruktion",)
    assert [item.sequence for item in merged.document.items] == [1, 2, 3, 4]


def test_an_expanded_last_child_stays_in_the_part_under_the_teachers_instruction() -> None:
    document, progress = _q2_q3_part()
    teacher_head = _teacher_edited_part(document)

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", [placeholder("p2", "Källtext två")]),
                    ("q3", [choice("p3", "Fråga tre a"), choice("p3b", "Fråga tre b")]),
                ],
                pending=(),
            )
        ),
    )

    (parent,) = merged.document.parents
    assert parent.item_ids == ("item_002", "item_003", "item_1001")
    assert body_text_lines(parent.instruction) == ("Lärarens instruktion",)
    assert [item.sequence for item in merged.document.items] == [1, 2, 3, 4]
