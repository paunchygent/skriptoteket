"""Progressive conversion merge: converted batches fill only untouched placeholders (D30)."""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    ConversionUnitState,
    abandon_target,
    first_conversion,
    merge_conversion,
    target_from_update,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
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


def test_teacher_edited_placeholder_keeps_teacher_version_and_drops_late_results(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    edited = head.items[1].model_copy(update={"body": body("Lärarens egen fråga")})
    teacher_head = _teacher_save(head, items=(head.items[0], edited, head.items[2]))
    converted_q2 = [choice("p2", "Fråga två")]

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", converted_q2),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q3",),
            )
        ),
    )
    assert _texts(merged.document) == ["Fråga ett", "Lärarens egen fråga", "Källtext tre"]
    unit = next(u for u in merged.progress.units if u.unit_id == "q2")
    assert unit.state is ConversionUnitState.TEACHER_KEPT

    # A later final result for the same question is dropped as well.
    final = merge_conversion(
        head=merged.document,
        progress=merged.progress,
        target=target_from_update(
            conversion_update(
                [
                    ("q1", [choice("p1", "Fråga ett")]),
                    ("q2", [choice("p2", "Fråga två igen")]),
                    ("q3", [choice("p3", "Fråga tre")]),
                ],
                pending=(),
            )
        ),
    )
    assert _texts(final.document) == ["Fråga ett", "Lärarens egen fråga", "Fråga tre"]


def test_teacher_deleted_placeholder_stays_deleted(
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
                    ("q2", [choice("p2", "Fråga två")]),
                    ("q3", [placeholder("p3", "Källtext tre")]),
                ],
                pending=("q3",),
            )
        ),
    )
    assert _texts(merged.document) == ["Fråga ett", "Källtext tre"]


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


def test_final_parents_map_to_saved_ids_and_an_invalid_parent_is_dropped(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    final_units = [
        ("q1", [choice("p1", "Fråga ett")]),
        ("q2", [choice("p2", "Fråga två")]),
        ("q3", [choice("p3", "Fråga tre")]),
    ]
    merged = merge_conversion(
        head=head,
        progress=progress,
        target=target_from_update(
            conversion_update(final_units, pending=(), parents=(("P", ("q1", "q2", "q3")),))
        ),
    )
    assert [p.item_ids for p in merged.document.parents] == [("item_001", "item_002", "item_003")]

    # The teacher rewrote q2's placeholder, so the parent would mix kinds: it is dropped.
    edited = head.items[1].model_copy(update={"body": body("Lärarens egen fråga")})
    teacher_head = _teacher_save(head, items=(head.items[0], edited, head.items[2]))
    kept = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=target_from_update(
            conversion_update(final_units, pending=(), parents=(("P", ("q1", "q2", "q3")),))
        ),
    )
    assert kept.document.parents == ()
    assert _texts(kept.document) == ["Fråga ett", "Lärarens egen fråga", "Fråga tre"]


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


def test_abandon_turns_only_untouched_placeholders_into_review_items(
    first: tuple[NativeExamDocument, ConversionProgress],
) -> None:
    head, progress = first
    edited = head.items[1].model_copy(update={"body": body("Lärarens egen fråga")})
    teacher_head = _teacher_save(head, items=(head.items[0], edited, head.items[2]))

    merged = merge_conversion(
        head=teacher_head,
        progress=progress,
        target=abandon_target(
            head=teacher_head, progress=progress, reason="Konverteringen stoppades."
        ),
    )
    reasons = [item.review.reasons for item in merged.document.items]
    assert reasons == [(), (PLACEHOLDER_REASON,), ("Konverteringen stoppades.",)]
    assert merged.progress.questions_done == 3
