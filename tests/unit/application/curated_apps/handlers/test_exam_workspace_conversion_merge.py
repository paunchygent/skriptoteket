"""Progressive conversion merge: a later batch always replaces its own placeholders (D30)."""

from __future__ import annotations

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    ConversionUnitState,
    abandon_target,
    changed_placeholders,
    first_conversion,
    merge_conversion,
    target_from_update,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_merge_test_support import (  # noqa: E501
    _teacher_save,
    _texts,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    PLACEHOLDER_REASON,
    body,
    choice,
    conversion_update,
    placeholder,
)


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


def test_receipt_survives_first_save_merge_and_abandonment_without_implying_readiness() -> None:
    progress = ConversionProgress.from_question_ids(("q1", "q2"))
    progress = progress.model_copy(update={"received_question_ids": ("q2",)})
    progress = ConversionProgress.model_validate_json(progress.model_dump_json())
    update = conversion_update(
        [("q1", [choice("p1", "Fråga ett")]), ("q2", [placeholder("p2", "Källtext två")])],
        pending=("q2",),
    )
    first = first_conversion(update=update, progress=progress)
    assert first.progress.received_question_ids == ("q2",)
    assert (first.progress.questions_received, first.progress.questions_done) == (1, 1)
    assert first.progress.units[1].state is ConversionUnitState.CONVERTING
    repeated = merge_conversion(
        head=first.document, progress=first.progress, target=target_from_update(update)
    )
    assert not repeated.changed
    assert repeated.progress.received_question_ids == ("q2",)
    abandoned = merge_conversion(
        head=first.document,
        progress=first.progress,
        target=abandon_target(head=first.document, progress=first.progress, reason="Avbruten"),
    )
    # A saved source-review fallback need not have received any converter output.
    assert abandoned.progress.questions_done == 2
    assert abandoned.progress.questions_received == 1
    assert abandoned.progress.received_question_ids == ("q2",)


def test_a_save_that_changes_a_placeholder_is_caught(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    edited = head.items[1].model_copy(update={"body": body("Lärarens redigerade källtext")})
    saved = _teacher_save(head, items=(head.items[0], edited, head.items[2]))

    assert changed_placeholders(progress=progress, base=head, saved=saved) == ["item_002"]


def _sectioned() -> tuple[NativeExamDocument, ConversionProgress]:
    merged = first_conversion(
        update=conversion_update(
            [
                ("q1", [choice("p1", "Fråga ett")]),
                ("q2", [placeholder("p2", "Källtext två")]),
                ("q3", [placeholder("p3", "Källtext tre")]),
            ],
            pending=("q2", "q3"),
            parents=(("section", ("q1", "q2", "q3")),),
        ),
        progress=ConversionProgress.from_question_ids(["q1", "q2", "q3"]),
    )
    return merged.document, merged.progress


def test_deleting_a_parented_placeholder_is_caught() -> None:
    """Review probe 1: the save removes the middle placeholder and its membership."""
    head, progress = _sectioned()
    q1, _, q3 = head.items
    saved = _teacher_save(
        head,
        items=(q1, q3.model_copy(update={"sequence": 2})),
        parents=(head.parents[0].model_copy(update={"item_ids": (q1.item_id, q3.item_id)}),),
    )

    assert changed_placeholders(progress=progress, base=head, saved=saved) == ["item_002"]


def test_giving_a_placeholder_id_to_a_teacher_question_is_caught() -> None:
    """Review probe 2: the last placeholder goes and a teacher question takes its id."""
    head, progress = _sectioned()
    q1, q2, q3 = head.items
    teacher_question = q3.model_copy(
        update={
            "body": body("Lärarens nya fråga"),
            "source_anchor": None,
            "review": q3.review.model_copy(
                update={"parse_origin": NativeParseOrigin.TEACHER_CREATED, "reasons": ()}
            ),
        }
    )
    saved = _teacher_save(
        head,
        items=(q1, q2, teacher_question),
        parents=(head.parents[0].model_copy(update={"item_ids": (q1.item_id, q2.item_id)}),),
    )

    assert changed_placeholders(progress=progress, base=head, saved=saved) == ["item_003"]


def test_moving_a_placeholder_out_of_its_parent_or_order_is_caught() -> None:
    head, progress = _sectioned()
    q1, q2, q3 = head.items
    swapped = _teacher_save(
        head,
        items=(
            q1,
            q3.model_copy(update={"sequence": 2}),
            q2.model_copy(update={"sequence": 3}),
        ),
        parents=(
            head.parents[0].model_copy(update={"item_ids": (q1.item_id, q3.item_id, q2.item_id)}),
        ),
    )
    unparented = _teacher_save(
        head, parents=(head.parents[0].model_copy(update={"item_ids": (q1.item_id,)}),)
    )

    assert changed_placeholders(progress=progress, base=head, saved=swapped) == [
        "item_002",
        "item_003",
    ]
    assert changed_placeholders(progress=progress, base=head, saved=unparented) == [
        "item_002",
        "item_003",
    ]


def test_editing_converted_items_and_adding_questions_leaves_placeholders_alone() -> None:
    head, progress = _sectioned()
    q1, q2, q3 = head.items
    added = q1.model_copy(update={"item_id": "item_004", "sequence": 4, "source_anchor": None})
    saved = _teacher_save(
        head,
        items=(q1.model_copy(update={"body": body("Lärarens fråga ett")}), q2, q3, added),
    )

    assert changed_placeholders(progress=progress, base=head, saved=saved) == []


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
    edited = head.items[0].model_copy(update={"body": body("Lärarens egen fråga")})
    teacher_head = _teacher_save(head, items=(edited, *head.items[1:]))

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=abandon_target(head=teacher_head, progress=progress, reason="Stoppad."),
    )
    assert _texts(merged.document)[0] == "Lärarens egen fråga"
    reasons = [item.review.reasons for item in merged.document.items]
    assert reasons == [(), ("Stoppad.",), ("Stoppad.",)]
    assert all(PLACEHOLDER_REASON not in r for r in reasons)
    assert merged.progress.questions_done == 3
