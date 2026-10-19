"""QTI import mapping: unsupported items and notes.

Split from test_qti_import_mapping.py by tested responsibility. Covers invalid
and unsupported items becoming Swedish notes, and the empty-import refusal.
"""

from dataclasses import replace
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import import (
    build_native_exam_from_qti,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_ordering_item,
)
from tests.unit.domain.curated_apps.exam_workspace.qti_import_mapping_support import (
    _SOURCE_SHA,
    _document,
    _imported,
    _qti_item,
)


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
