"""Round-trip proof for the read QTI -> native exam mapper.

Every native document is built with the existing test builders, exported through
``native_exam_to_examnet_qti_items`` and imported again. The projections compare
positions and payload hashes, never regenerated identifiers.
"""

import hashlib
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiPackageItemSource,
    ExamNetQtiPackageSource,
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamImportRecord,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
    validate_parent_structure,
)
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
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.application.curated_apps.qti_round_trip_support import (
    _body_projection,
    _document_projection,
    _position,
    _positions,
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

PNG_ONE = b"\x89PNG\r\n\x1a\nfirst picture"
PNG_TWO = b"\x89PNG\r\n\x1a\nsecond picture"
_ASSET_ONE = "asset_1111111111111111"
_ASSET_TWO = "asset_2222222222222222"
_SOURCE_SHA = "a" * 64


def _asset(asset_id: str, payload: bytes) -> NativeExamAsset:
    return NativeExamAsset(
        asset_id=asset_id,
        sha256=hashlib.sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )


def _document(
    items: tuple[NativeExamItem, ...],
    *,
    assets: tuple[NativeExamAsset, ...] = (),
    parents: tuple[NativeExamParent, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov på svenska",
        items=items,
        parents=parents,
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _at(item: NativeExamItem, sequence: int) -> NativeExamItem:
    return NativeExamItem.model_validate(
        {**dict(item), "item_id": f"item_{sequence:03d}", "sequence": sequence}
    )


def _round_trip(
    document: NativeExamDocument,
    payloads: dict[str, bytes] | None = None,
) -> tuple[tuple[ExamNetQtiItem, ...], ExamWorkspaceContainerContent]:
    items = native_exam_to_examnet_qti_items(document, assets_by_id=payloads or {})
    container = build_native_exam_from_qti(
        items=items,
        document_id=uuid4(),
        source_filename="omprov.qti.zip",
        source_sha256=_SOURCE_SHA,
    )
    return items, container


def _qti_item(
    interaction: ExamNetQtiInteractionType,
    *,
    sequence: int,
    opening: str = "Fråga",
    choices: tuple[ExamNetQtiChoice, ...] = (),
    correct_choice_identifiers: tuple[str, ...] = (),
    inline_choice_gaps: tuple[ExamNetQtiInlineChoiceGap, ...] = (),
    match_left: tuple[ExamNetQtiMatchEntry, ...] = (),
    match_right: tuple[ExamNetQtiMatchEntry, ...] = (),
    match_pairs: tuple[ExamNetQtiMatchPair, ...] = (),
    children: tuple[ExamNetQtiItem, ...] = (),
) -> ExamNetQtiItem:
    """A read QTI item built by hand, independent of what the exporter produces."""

    return ExamNetQtiItem(
        item_id=f"item_{sequence:03d}",
        sequence=sequence,
        title=opening,
        interaction_type=interaction,
        prompt_lines=(opening,),
        max_score=1,
        choices=choices,
        correct_choice_identifiers=correct_choice_identifiers,
        inline_choice_gaps=inline_choice_gaps,
        match_left=match_left,
        match_right=match_right,
        match_pairs=match_pairs,
        children=children,
    )


def _imported(*items: ExamNetQtiItem) -> tuple[tuple[NativeExamItem, ...], tuple[str, ...]]:
    container = build_native_exam_from_qti(
        items=items,
        document_id=uuid4(),
        source_filename="robust.zip",
        source_sha256=_SOURCE_SHA,
    )
    return container.document.items, container.notes


def _prompt_projection(item: ExamNetQtiItem) -> tuple[object, ...]:
    return tuple(
        (
            paragraph.heading_level,
            tuple(
                ("text", segment.text, tuple(segment.marks))
                if isinstance(segment, ExamNetQtiPromptText)
                else ("image", segment.image_index)
                if isinstance(segment, ExamNetQtiPromptImage)
                else ("gap", segment.gap_index)
                for segment in paragraph.segments
            ),
        )
        for paragraph in item.prompt_paragraphs
    )


def _deduped(values: tuple[str, ...]) -> tuple[str, ...]:
    kept: list[str] = []
    for value in values:
        stripped = value.strip()
        if stripped and stripped not in kept:
            kept.append(stripped)
    return tuple(kept)


def _qti_projection(item: ExamNetQtiItem) -> dict[str, object]:
    choice_ids = [choice.identifier for choice in item.choices]
    left_ids = [entry.identifier for entry in item.match_left]
    right_ids = [entry.identifier for entry in item.match_right]
    return {
        "interaction": item.interaction_type.value,
        "prompt": _prompt_projection(item),
        "max_score": item.max_score,
        "choices": tuple(choice.text for choice in item.choices),
        "correct": _positions(choice_ids, item.correct_choice_identifiers),
        "gaps": tuple(_deduped(gap.accepted_values) for gap in item.text_entry_gaps),
        "inline": tuple(
            (
                tuple(option.text for option in gap.options),
                _position(
                    [option.identifier for option in gap.options],
                    gap.correct_option_identifier,
                ),
            )
            for gap in item.inline_choice_gaps
        ),
        "match_left": tuple(entry.text for entry in item.match_left),
        "match_right": tuple(entry.text for entry in item.match_right),
        "pairs": tuple(
            (left_ids.index(pair.left_identifier), right_ids.index(pair.right_identifier))
            for pair in item.match_pairs
        ),
        "children": tuple(_qti_projection(child) for child in item.children),
    }


def _export_projection(items: tuple[ExamNetQtiItem, ...]) -> tuple[object, ...]:
    return tuple(_qti_projection(item) for item in items)


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


def test_two_child_parent_keeps_the_stem_picture_and_each_childs_picture() -> None:
    payloads = {_ASSET_ONE: PNG_ONE, _ASSET_TWO: PNG_TWO}
    pictured_child = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Före ", marks=()),
                    NativeAssetSegment(asset_id=_ASSET_TWO),
                    NativeTextSegment(text=" efter.", marks=()),
                ),
            ),
        ),
        points=1,
        choices=(
            NativeChoice(choice_id="choice_001", body=plain_body("Ett")),
            NativeChoice(choice_id="choice_002", body=plain_body("Två")),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            correct_choice_ids=("choice_002",),
        ),
        review=make_review(),
    )
    parent = NativeExamParent(
        parent_id="parent_001",
        place=pictured_child.sequence - 1,
        instruction=(
            NativeParagraph(
                heading_level=2,
                segments=(
                    NativeTextSegment(text="Läs texten ", marks=("italic",)),
                    NativeAssetSegment(asset_id=_ASSET_ONE),
                ),
            ),
        ),
        item_ids=("item_001", "item_002"),
    )
    document = _document(
        (pictured_child, _at(make_single_choice_item(), 2)),
        assets=(_asset(_ASSET_ONE, PNG_ONE), _asset(_ASSET_TWO, PNG_TWO)),
        parents=(parent,),
    )

    first_items, container = _round_trip(document, payloads)
    imported = container.document
    sha_by_asset_id = {asset.asset_id: asset.sha256 for asset in imported.assets}

    assert _document_projection(imported) == _document_projection(document)
    assert imported.parents[0].item_ids == ("item_001", "item_002")
    assert _body_projection(imported.parents[0].instruction, sha_by_asset_id)[0][1][1] == (
        "asset",
        hashlib.sha256(PNG_ONE).hexdigest(),
    )
    assert (
        "asset",
        hashlib.sha256(PNG_TWO).hexdigest(),
    ) in _body_projection(imported.items[0].body, sha_by_asset_id)[0][1]
    assert set(container.assets_by_id.values()) == {PNG_ONE, PNG_TWO}
    second_items = native_exam_to_examnet_qti_items(imported, assets_by_id=container.assets_by_id)
    assert _export_projection(second_items) == _export_projection(first_items)
    (parent_qti,) = second_items
    assert len(parent_qti.image_resources) == 2
    assert [len(child.image_resources) for child in parent_qti.children] == [1, 0]


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


def test_unsupported_items_give_the_exact_swedish_notes_in_order() -> None:
    (supported,) = native_exam_to_examnet_qti_items(_document((make_free_text_item(),)))
    items = (
        ExamNetQtiUnsupportedItem(
            sequence=1,
            opening_text="Första frågan",
            reason=ExamNetQtiUnsupportedReason.INTERACTION,
        ),
        ExamNetQtiUnsupportedItem(
            sequence=2,
            opening_text="",
            reason=ExamNetQtiUnsupportedReason.IMAGE,
        ),
        ExamNetQtiUnsupportedItem(
            sequence=3,
            opening_text="x" * 120,
            reason=ExamNetQtiUnsupportedReason.IMAGE,
        ),
        supported,
    )

    container = build_native_exam_from_qti(
        items=items,
        document_id=uuid4(),
        source_filename="blandat.zip",
        source_sha256=_SOURCE_SHA,
    )

    assert container.notes == (
        "Fråga 1 – Första frågan: frågetypen stöds inte och importerades inte.",
        "Fråga 2: en bild i frågan kunde inte läsas och frågan importerades inte.",
        f"Fråga 3 – {'x' * 100}: en bild i frågan kunde inte läsas och frågan importerades inte.",
    )
    assert len(container.document.items) == 1
    assert container.document.items[0].sequence == 1


def test_only_unsupported_items_raise_the_swedish_validation_error() -> None:
    unsupported = ExamNetQtiUnsupportedItem(
        sequence=1,
        opening_text="Första frågan",
        reason=ExamNetQtiUnsupportedReason.INTERACTION,
    )

    with pytest.raises(DomainError) as exc_info:
        build_native_exam_from_qti(
            items=(unsupported,),
            document_id=uuid4(),
            source_filename="bara-stodda.zip",
            source_sha256=_SOURCE_SHA,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == "QTI-paketet innehåller inga frågetyper som stöds."


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


def test_an_ordering_item_with_a_broken_key_becomes_an_interaction_note() -> None:
    (supported,) = native_exam_to_examnet_qti_items(_document((make_free_text_item(),)))
    (ordering,) = native_exam_to_examnet_qti_items(_document((make_ordering_item(),)))
    broken = replace(
        ordering,
        correct_choice_identifiers=ordering.correct_choice_identifiers[:-1],
    )

    container = build_native_exam_from_qti(
        items=(supported, broken),
        document_id=uuid4(),
        source_filename="ordning.zip",
        source_sha256=_SOURCE_SHA,
    )

    assert [item.kind for item in container.document.items] == [NativeExamItemKind.FREE_TEXT]
    assert container.notes == (
        "Fråga 1 – Sätt stegen i en argumenterande text i rätt ordning.: "
        "frågetypen stöds inte och importerades inte.",
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


def test_document_metadata_is_revision_one_with_the_qti_import_origin() -> None:
    document_id = uuid4()
    course = ExamCourseChoice(key="matematik", name="Matematik")
    (item,) = native_exam_to_examnet_qti_items(_document((make_free_text_item(),)))

    container = build_native_exam_from_qti(
        items=(item,),
        document_id=document_id,
        source_filename="omprov-i-matematik.qti.zip",
        source_sha256=_SOURCE_SHA,
        course=course,
    )

    document = container.document
    assert document.document_id == document_id
    assert document.revision == 1
    assert document.title == "omprov-i-matematik.qti"
    assert document.header.course == course
    assert document.origin.kind == "qti_import"
    assert document.origin.source_filename == "omprov-i-matematik.qti.zip"
    assert document.origin.source_sha256 == _SOURCE_SHA


def test_repeated_picture_payloads_become_one_asset() -> None:
    first = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(
            NativeParagraph(
                heading_level=None,
                segments=(NativeAssetSegment(asset_id=_ASSET_ONE),),
            ),
        ),
        points=1,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=make_review(),
    )
    second = NativeExamItem.model_validate(
        {
            **dict(first),
            "item_id": "item_002",
            "sequence": 2,
            "body": (
                NativeParagraph(
                    heading_level=None,
                    segments=(NativeAssetSegment(asset_id=_ASSET_TWO),),
                ),
            ),
        }
    )
    document = _document(
        (first, second),
        assets=(_asset(_ASSET_ONE, PNG_ONE), _asset(_ASSET_TWO, PNG_ONE)),
    )

    _, container = _round_trip(document, {_ASSET_ONE: PNG_ONE, _ASSET_TWO: PNG_ONE})

    assert len(container.document.assets) == 1
    assert list(container.assets_by_id.values()) == [PNG_ONE]


def test_the_read_contracts_keep_package_items_in_test_order() -> None:
    item_source = ExamNetQtiPackageItemSource(path="items/item_001.xml", xml=b"<item/>")
    package = ExamNetQtiPackageSource(
        items=(item_source,),
        files={"items/item_001.xml": b"<item/>", "assessment.xml": b"<test/>"},
    )

    assert package.items == (item_source,)
    assert package.files["assessment.xml"] == b"<test/>"
    assert isinstance(package.files, dict)


def test_a_single_choice_with_two_correct_identifiers_becomes_a_note_and_keeps_others() -> None:
    invalid = _qti_item(
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        sequence=1,
        opening="Välj ett alternativ",
        choices=(
            ExamNetQtiChoice(identifier="c1", text="Ett"),
            ExamNetQtiChoice(identifier="c2", text="Två"),
            ExamNetQtiChoice(identifier="c3", text="Tre"),
        ),
        correct_choice_identifiers=("c1", "c3"),
    )
    valid = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=2, opening="Resonera")

    items, notes = _imported(invalid, valid)

    assert [item.kind for item in items] == [NativeExamItemKind.FREE_TEXT]
    assert notes == ("Fråga 1 – Välj ett alternativ: frågetypen stöds inte och importerades inte.",)


def test_a_choice_item_with_one_choice_becomes_a_note() -> None:
    invalid = _qti_item(
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        sequence=1,
        opening="Bara ett alternativ",
        choices=(ExamNetQtiChoice(identifier="c1", text="Ett"),),
        correct_choice_identifiers=("c1",),
    )
    valid = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=2, opening="Resonera")

    items, notes = _imported(invalid, valid)

    assert [item.kind for item in items] == [NativeExamItemKind.FREE_TEXT]
    assert notes == ("Fråga 1 – Bara ett alternativ: frågetypen stöds inte och importerades inte.",)


def test_a_correct_identifier_naming_no_choice_becomes_a_note() -> None:
    invalid = _qti_item(
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        sequence=1,
        opening="Okänt facit",
        choices=(
            ExamNetQtiChoice(identifier="c1", text="Ett"),
            ExamNetQtiChoice(identifier="c2", text="Två"),
        ),
        correct_choice_identifiers=("saknas",),
    )
    valid = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=2, opening="Resonera")

    items, notes = _imported(invalid, valid)

    assert [item.kind for item in items] == [NativeExamItemKind.FREE_TEXT]
    assert notes == ("Fråga 1 – Okänt facit: frågetypen stöds inte och importerades inte.",)


def test_a_match_pair_naming_an_unknown_left_identifier_becomes_a_note() -> None:
    invalid = _qti_item(
        ExamNetQtiInteractionType.MATCHING,
        sequence=1,
        opening="Para ihop",
        match_left=(ExamNetQtiMatchEntry(identifier="l1", text="Hund"),),
        match_right=(
            ExamNetQtiMatchEntry(identifier="r1", text="Däggdjur"),
            ExamNetQtiMatchEntry(identifier="r2", text="Fåglar"),
        ),
        match_pairs=(
            ExamNetQtiMatchPair(
                left_identifier="saknas",
                left_text="?",
                right_identifier="r1",
                right_text="Däggdjur",
            ),
        ),
    )
    valid = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=2, opening="Resonera")

    items, notes = _imported(invalid, valid)

    assert [item.kind for item in items] == [NativeExamItemKind.FREE_TEXT]
    assert notes == ("Fråga 1 – Para ihop: frågetypen stöds inte och importerades inte.",)


def test_an_inline_correct_option_naming_no_option_becomes_a_note() -> None:
    invalid = _qti_item(
        ExamNetQtiInteractionType.INLINE_CHOICE,
        sequence=1,
        opening="Välj i listan",
        inline_choice_gaps=(
            ExamNetQtiInlineChoiceGap(
                response_identifier="g1",
                options=(
                    ExamNetQtiChoice(identifier="o1", text="Alfa"),
                    ExamNetQtiChoice(identifier="o2", text="Beta"),
                ),
                correct_option_identifier="saknas",
            ),
        ),
    )
    valid = _qti_item(ExamNetQtiInteractionType.FREE_TEXT, sequence=2, opening="Resonera")

    items, notes = _imported(invalid, valid)

    assert [item.kind for item in items] == [NativeExamItemKind.FREE_TEXT]
    assert notes == ("Fråga 1 – Välj i listan: frågetypen stöds inte och importerades inte.",)


def test_an_ordering_child_in_a_parent_becomes_a_note_and_the_parent_keeps_its_other_child() -> (
    None
):
    ordering_child = _qti_item(
        ExamNetQtiInteractionType.ORDERING,
        sequence=1,
        opening="Sortera stegen",
        choices=(
            ExamNetQtiChoice(identifier="s1", text="Tes"),
            ExamNetQtiChoice(identifier="s2", text="Argument"),
        ),
        correct_choice_identifiers=("s1", "s2"),
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

    assert [item.kind for item in container.document.items] == [NativeExamItemKind.FREE_TEXT]
    assert container.document.parents[0].place == 0
    assert container.document.parents[0].item_ids == ("item_001",)
    assert container.notes == (
        "Fråga 1 – Sortera stegen: frågetypen stöds inte och importerades inte.",
    )


def test_a_package_with_only_an_invalid_item_raises_the_swedish_validation_error() -> None:
    invalid = _qti_item(
        ExamNetQtiInteractionType.SINGLE_CHOICE,
        sequence=1,
        opening="Bara ett alternativ",
        choices=(ExamNetQtiChoice(identifier="c1", text="Ett"),),
        correct_choice_identifiers=("c1",),
    )

    with pytest.raises(DomainError) as exc_info:
        build_native_exam_from_qti(
            items=(invalid,),
            document_id=uuid4(),
            source_filename="trasigt.zip",
            source_sha256=_SOURCE_SHA,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.message == "QTI-paketet innehåller inga frågetyper som stöds."


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
