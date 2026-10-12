"""Progressive conversion merge: a later batch always replaces its own placeholders (D30)."""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionMerge,
    ConversionProgress,
    ConversionUnitState,
    abandon_target,
    first_conversion,
    merge_conversion,
    target_from_update,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItemKind,
    NativeTextSegment,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    PLACEHOLDER_REASON,
    body,
    choice,
    conversion_update,
    placeholder,
)


def _teacher_save(document: NativeExamDocument, **changes: object) -> NativeExamDocument:
    return NativeExamDocument.model_validate(
        document.model_copy(update={"revision": document.revision + 1, **changes}).model_dump()
    )


def _texts(document: NativeExamDocument) -> list[str]:
    return [
        "".join(s.text for s in item.body[0].segments if isinstance(s, NativeTextSegment))
        for item in document.items
    ]


@pytest.fixture
def first() -> tuple[NativeExamDocument, ConversionProgress]:
    progress = ConversionProgress.from_question_ids(["q1", "q2", "q3"])
    merged = first_conversion(
        update=conversion_update(
            [
                ("q1", [choice("p1", "Fråga ett")]),
                ("q2", [placeholder("p2", "Källtext två")]),
                ("q3", [placeholder("p3", "Källtext tre")]),
            ],
            pending=("q2", "q3"),
        ),
        progress=progress,
    )
    return merged.document, merged.progress


def test_untouched_placeholder_is_replaced_in_place_by_its_converted_items(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    update = conversion_update(
        [
            ("q1", [choice("p1", "Fråga ett")]),
            ("q2", [choice("p2", "Fråga två a"), choice("p2b", "Fråga två b")]),
            ("q3", [placeholder("p3", "Källtext tre")]),
        ],
        pending=("q3",),
    )

    merged = merge_conversion(head=head, progress=progress, target=target_from_update(update))

    assert _texts(merged.document) == ["Fråga ett", "Fråga två a", "Fråga två b", "Källtext tre"]
    assert [item.sequence for item in merged.document.items] == [1, 2, 3, 4]
    # The first converted item reuses the placeholder id; the second gets a fresh id.
    assert [item.item_id for item in merged.document.items] == [
        "item_001",
        "item_002",
        "item_1001",
        "item_003",
    ]
    assert merged.document.revision == head.revision + 1
    states = {unit.unit_id: unit.state for unit in merged.progress.units}
    assert states == {
        "q1": ConversionUnitState.READY,
        "q2": ConversionUnitState.READY,
        "q3": ConversionUnitState.CONVERTING,
    }
    assert merged.progress.questions_done == 2


def test_a_later_batch_replaces_a_placeholder_a_save_changed(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    edited = head.items[1].model_copy(
        update={"body": body("Lärarens egen fråga"), "title": "Lärarens rubrik"}
    )
    teacher_head = _teacher_save(head, items=(head.items[0], edited, head.items[2]))
    converted_q2 = choice("p2", "Fråga två")

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", [converted_q2]),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q3",),
            )
        ),
    )

    assert _texts(merged.document) == ["Fråga ett", "Fråga två", "Källtext tre"]
    q2 = merged.document.items[1]
    assert (q2.kind, q2.title, q2.review) == (
        converted_q2.kind,
        converted_q2.title,
        converted_q2.review,
    )
    unit = next(u for u in merged.progress.units if u.unit_id == "q2")
    assert unit.state is ConversionUnitState.READY
    assert merged.progress.questions_done == 2


def test_a_later_batch_restores_a_placeholder_a_save_deleted(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    teacher_head = _teacher_save(
        head,
        items=(
            head.items[0],
            head.items[2].model_copy(update={"sequence": 2}),
        ),
    )
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
                pending=("q3",),
            )
        ),
    )
    assert _texts(merged.document) == ["Fråga ett", "Fråga två a", "Fråga två b", "Källtext tre"]
    ids = [item.item_id for item in merged.document.items]
    assert len(set(ids)) == len(ids)


def test_teacher_edit_on_a_converted_item_survives_later_batches(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    edited = head.items[0].model_copy(update={"body": body("Lärarens fråga ett"), "points": 3})
    teacher_head = _teacher_save(head, items=(edited, *head.items[1:]))

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett igen")]),
                    ("q2", [choice("p2", "Fråga två")]),
                    ("q3", [choice("p3", "Fråga tre")]),
                ],
                pending=(),
            )
        ),
    )

    assert _texts(merged.document) == ["Lärarens fråga ett", "Fråga två", "Fråga tre"]
    assert merged.document.items[0].points == 3


def test_teacher_added_item_keeps_its_place_and_fresh_ids_never_collide(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    added = choice("", "Lärarens tillagda").model_copy(
        update={"item_id": "item_1001", "sequence": 2, "source_anchor": None}
    )
    items = (head.items[0], added, *head.items[1:])
    teacher_head = _teacher_save(
        head,
        items=tuple(item.model_copy(update={"sequence": i}) for i, item in enumerate(items, 1)),
    )
    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", [choice("p2", "Två a"), choice("p2b", "Två b")]),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q3",),
            )
        ),
    )
    assert _texts(merged.document) == [
        "Fråga ett",
        "Lärarens tillagda",
        "Två a",
        "Två b",
        "Källtext tre",
    ]
    ids = [item.item_id for item in merged.document.items]
    assert len(set(ids)) == len(ids)
    assert ids[1] == "item_1001"


def test_teacher_title_wins_over_the_final_title(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    teacher_head = _teacher_save(head, title="Lärarens rubrik")
    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [("q1", [choice("p1", "Fråga ett")])], pending=(), title="Provets rubrik"
            )
        ),
    )
    assert merged.document.title == "Lärarens rubrik"

    untouched = merge_conversion(
        head=head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [("q1", [choice("p1", "Fråga ett")])], pending=(), title="Provets rubrik"
            )
        ),
    )
    assert untouched.document.title == "Provets rubrik"


def test_final_parents_map_to_saved_ids(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    merged = _final_with_parent(head, progress)
    assert [p.item_ids for p in merged.document.parents] == [("item_001", "item_002", "item_003")]


def test_question_less_review_item_from_the_final_is_inserted_after_its_preceding_unit(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    unplaced = placeholder("p2x", "Oplacerad källtext").model_copy(
        update={
            "review": placeholder("p2x", "x").review.model_copy(
                update={"reasons": ("Kontrollera.",)}
            )
        }
    )
    update = conversion_update(
        [
            ("q1", [choice("p1", "Fråga ett")]),
            ("q2", [choice("p2", "Fråga två")]),
            ("q3", [choice("p3", "Fråga tre")]),
        ],
        pending=(),
        extras=(unplaced,),
    )
    # The pipeline orders the unplaced chunk between q2 and q3 in source order.
    reordered = update.document.items
    items = (reordered[0], reordered[1], reordered[3], reordered[2])
    document = update.document.model_copy(
        update={
            "items": tuple(i.model_copy(update={"sequence": n}) for n, i in enumerate(items, 1))
        }
    )
    target = target_from_update(
        ConversionUpdate(
            filled=update.filled,
            pending=(),
            document=document,
            item_ids=update.item_ids,
            extra_item_ids=update.extra_item_ids,
            parent_ids={},
        )
    )
    merged = merge_conversion(head=head, progress=progress, target=target)
    assert _texts(merged.document) == ["Fråga ett", "Fråga två", "Oplacerad källtext", "Fråga tre"]


def test_abandon_turns_every_still_converting_placeholder_into_a_review_item(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    edited = head.items[1].model_copy(update={"body": body("Lärarens egen fråga")})
    teacher_head = _teacher_save(head, items=(head.items[0], edited, head.items[2]))

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=abandon_target(head=teacher_head, progress=progress, reason="Stoppad."),
    )
    reasons = [item.review.reasons for item in merged.document.items]
    assert reasons == [(), ("Stoppad.",), ("Stoppad.",)]
    assert all(PLACEHOLDER_REASON not in r for r in reasons)
    assert merged.progress.questions_done == 3


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
        item.item_id: (parent.instruction if (parent := document.parent_of(item.item_id)) else None)
        for item in document.items
    }


def test_teacher_retitled_converted_child_stays_under_the_final_parent(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    retitled = head.items[0].model_copy(update={"title": "Lärarens titel"})
    teacher_head = _teacher_save(head, items=(retitled, *head.items[1:]))

    merged = _final_with_parent(teacher_head, progress)

    assert merged.document.items[0].title == "Lärarens titel"
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


def test_a_placeholder_child_a_save_changed_is_replaced_by_its_converted_child(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    # The staging walk: the teacher typed a heading into a placeholder child of a parent.
    edited = head.items[1].model_copy(update={"title": "Lärarens rubrik"})
    teacher_head = _teacher_save(head, items=(head.items[0], edited, head.items[2]))

    merged = _final_with_parent(teacher_head, progress)

    assert _texts(merged.document) == ["Fråga ett", "Fråga två", "Fråga tre"]
    assert {item.kind for item in merged.document.items} == {NativeExamItemKind.SINGLE_CHOICE}
    assert merged.document.items[1].title is None
    assert [p.item_ids for p in merged.document.parents] == [("item_001", "item_002", "item_003")]
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
