"""QTI import mapping: leaf item kinds.

Split from test_qti_import_mapping.py by tested responsibility. Covers the
supported leaf kinds (choice, gap fill, inline choice, free text, matching,
ordering) including points, keys, and import records.
"""

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamImportRecord,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import import (
    build_native_exam_from_qti,
)
from tests.unit.application.curated_apps.qti_round_trip_support import (
    _document_projection,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_ordering_item,
    make_review,
    make_single_choice_item,
    plain_body,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)
from tests.unit.domain.curated_apps.exam_workspace.qti_import_mapping_support import (
    _SOURCE_SHA,
    _at,
    _document,
    _export_projection,
    _round_trip,
)


def test_every_supported_kind_round_trips_and_reexports_identically() -> None:
    multiple_response = NativeExamItem(
        item_id="item_003",
        sequence=3,
        kind=NativeExamItemKind.MULTIPLE_RESPONSE,
        body=plain_body("Markera alla rätt."),
        points=3,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
            NativeChoice(choice_id="choice_002", body=plain_body("Två")),
            NativeChoice(choice_id="choice_003", body=plain_body("Tre")),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            correct_choice_ids=("choice_001", "choice_003"),
        ),
        review=make_review(),
    )
    document = _document(
        (
            _at(make_free_text_item(), 1),
            _at(make_single_choice_item(), 2),
            multiple_response,
            _at(make_gap_fill_item(), 4),
            _at(inline_choice_item(), 5),
            _at(matching_item(), 6),
            _at(make_ordering_item(), 7),
        )
    )

    first_items, container = _round_trip(document)

    assert _document_projection(container.document) == _document_projection(document)
    second_items = native_exam_to_examnet_qti_items(
        container.document, assets_by_id=container.assets_by_id
    )
    assert _export_projection(second_items) == _export_projection(first_items)


@pytest.mark.parametrize("points", [None, 2.5])
def test_gap_fill_points_come_from_the_package_max_score(points: int | float | None) -> None:
    item = NativeExamItem.model_validate({**dict(make_gap_fill_item()), "points": points})

    _, container = _round_trip(_document((item,)))

    imported = container.document.items[0]
    assert imported.points == points
    assert imported.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED


def test_gap_fill_keeps_a_fractional_max_score_across_two_gaps() -> None:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Första ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text=" och andra ", marks=()),
                    NativeGapSegment(gap_id="gap_002"),
                ),
            ),
        ),
        points=2.01,
        gaps=(
            NativeGap(gap_id="gap_001", accepted_values=("ett",)),
            NativeGap(gap_id="gap_002", accepted_values=("två",)),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=make_review(),
    )

    _, container = _round_trip(_document((item,)))

    imported = container.document.items[0]
    assert imported.points == 2.01
    assert imported.tick_points is None
    assert [gap.accepted_values for gap in imported.body_gaps()] == [("ett",), ("två",)]


def test_gap_fill_merges_automatic_spellings_into_the_imported_key() -> None:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Ämnet: ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                ),
            ),
        ),
        points=1,
        gaps=(
            NativeGap(
                gap_id="gap_001",
                accepted_values=("nationalekonomi",),
                automatic_values=("nationalekonomie",),
            ),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=make_review(),
    )

    _, container = _round_trip(_document((item,)))

    assert container.document.items[0].gaps[0].accepted_values == (
        "nationalekonomi",
        "nationalekonomie",
    )


def test_gap_fill_strips_and_deduplicates_package_values() -> None:
    (exported,) = native_exam_to_examnet_qti_items(_document((make_gap_fill_item(),)))
    dirty = replace(
        exported,
        text_entry_gaps=(
            replace(
                exported.text_entry_gaps[0],
                accepted_values=("  NF ", "NF", "", "  ", "nf"),
            ),
        ),
    )

    container = build_native_exam_from_qti(
        items=(dirty,),
        document_id=uuid4(),
        source_filename="smutsigt-facit.zip",
        source_sha256=_SOURCE_SHA,
    )

    assert container.document.items[0].gaps[0].accepted_values == ("NF", "nf")


def test_an_unkeyed_choice_item_stays_absent_with_no_key_data() -> None:
    item = make_single_choice_item(origin=NativeAnswerKeyOrigin.ABSENT, correct=())

    _, container = _round_trip(_document((item,)))

    imported = container.document.items[0]
    assert imported.points == item.points
    assert imported.answer_key.origin is NativeAnswerKeyOrigin.ABSENT
    assert imported.answer_key.correct_choice_ids == ()
    assert imported.import_record is not None
    assert imported.import_record.original_wording.answer_key_text is None


def test_free_text_criteria_are_a_named_loss_while_points_are_kept() -> None:
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=plain_body("Resonera om renässansen."),
        points=3,
        criteria=(
            NativeExamCriterion(text="Ett korrekt exempel.", points=2),
            NativeExamCriterion(text="En korrekt förklaring.", points=1),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=make_review(),
    )

    _, container = _round_trip(_document((item,)))

    imported = container.document.items[0]
    assert imported.criteria == ()
    assert imported.points == 3
    assert imported.answer_key.origin is NativeAnswerKeyOrigin.NOT_APPLICABLE
    assert imported.import_record is not None
    assert imported.import_record.original_wording.answer_key_text is None


def test_a_partially_keyed_gap_fill_is_absent_and_drops_every_value() -> None:
    native = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Första ", marks=()),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text=" och andra ", marks=()),
                    NativeGapSegment(gap_id="gap_002"),
                ),
            ),
        ),
        points=2,
        gaps=(
            NativeGap(gap_id="gap_001", accepted_values=("ett",)),
            NativeGap(gap_id="gap_002", accepted_values=("två",)),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=make_review(),
    )
    (exported,) = native_exam_to_examnet_qti_items(_document((native,)))
    partial = replace(
        exported,
        text_entry_gaps=(
            exported.text_entry_gaps[0],
            replace(exported.text_entry_gaps[1], accepted_values=()),
        ),
    )

    container = build_native_exam_from_qti(
        items=(partial,),
        document_id=uuid4(),
        source_filename="halvt-facit.zip",
        source_sha256=_SOURCE_SHA,
    )

    imported = container.document.items[0]
    assert imported.answer_key.origin is NativeAnswerKeyOrigin.ABSENT
    assert [gap.accepted_values for gap in imported.gaps] == [(), ()]
    assert imported.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert imported.review.reasons == (
        "Facit saknades för en eller flera luckor och importerades inte.",
    )
    assert imported.import_record is not None
    assert imported.import_record.original_wording.answer_key_text is None


def test_matching_points_that_do_not_split_evenly_are_rounded_down_and_flagged() -> None:
    (exported,) = native_exam_to_examnet_qti_items(_document((matching_item(),)))
    uneven = replace(exported, max_score=10)

    container = build_native_exam_from_qti(
        items=(uneven,),
        document_id=uuid4(),
        source_filename="udda-poang.zip",
        source_sha256=_SOURCE_SHA,
    )

    imported = container.document.items[0]
    assert imported.points == 9.99
    assert imported.tick_points == Decimal("3.33")
    assert imported.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED
    assert len(imported.answer_key.match_pairs) == 3
    assert imported.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert imported.review.reasons == (
        "Poängen kunde inte delas lika mellan paren. Kontrollera poängen.",
    )


def test_import_records_snapshot_the_package_wording_and_key_per_kind() -> None:
    def imported(item: NativeExamItem) -> NativeExamImportRecord:
        _, container = _round_trip(_document((item,)))
        record = container.document.items[0].import_record
        assert record is not None
        return record

    free_text = imported(make_free_text_item())
    assert free_text.original_wording.question_text == "Resonera om renässansen."
    assert free_text.original_wording.answer_key_text is None
    assert [step.kind for step in free_text.steps] == ["chosen_type", "answer_key"]

    choice = imported(make_single_choice_item())
    assert choice.original_wording.question_text == "Vilket är huvudordet?"
    assert choice.original_wording.answer_key_text == "eleverna"

    gap_fill = imported(make_gap_fill_item())
    assert gap_fill.original_wording.question_text == "Ange frastyp: [___]"
    assert gap_fill.original_wording.answer_key_text == "NF"

    inline_choice = imported(inline_choice_item())
    assert inline_choice.original_wording.answer_key_text == ("Beta 2 & <text>\nAlfa 1 & <text>")

    matching = imported(matching_item())
    assert matching.original_wording.answer_key_text == (
        "hund – däggdjur\nkatt – fåglar\nfågel – fiskar"
    )

    ordering = imported(make_ordering_item())
    assert ordering.original_wording.answer_key_text == ("Tes\nArgument\nMotargument\nAvslutning")
