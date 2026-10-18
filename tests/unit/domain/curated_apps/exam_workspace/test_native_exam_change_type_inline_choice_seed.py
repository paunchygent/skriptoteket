"""Dropdown seed and key-provenance rules when a gap-fill item changes type."""

import random

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import change_item_type
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeGap
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_gap_fill_item,
)


def _typed_gap_item(
    values_by_gap: tuple[tuple[str, ...], ...],
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
    automatic_values: tuple[str, ...] = (),
    excluded_automatic_values: tuple[str, ...] = (),
) -> NativeExamItem:
    gaps = tuple(
        NativeGap(
            gap_id=f"gap_{i:03d}",
            accepted_values=values,
            automatic_values=automatic_values,
            excluded_automatic_values=excluded_automatic_values,
        )
        for i, values in enumerate(values_by_gap, start=1)
    )
    payload = make_gap_fill_item(
        origin=origin,
        accepted=() if origin is NativeAnswerKeyOrigin.ABSENT else ("NF",),
    ).model_dump()
    payload["gaps"] = gaps
    payload["body"] = (
        NativeParagraph(
            heading_level=None,
            segments=tuple(NativeGapSegment(gap_id=gap.gap_id) for gap in gaps),
        ),
    )
    return NativeExamItem.model_validate(payload)


def _option_text(segment: object) -> str:
    assert isinstance(segment, NativeTextSegment)
    return segment.text


def _option_texts(gap: NativeGap) -> list[tuple[str, str]]:
    return [(option.choice_id, _option_text(option.body[0].segments[0])) for option in gap.options]


def test_gap_fill_to_dropdown_seeds_options_from_accepted_values() -> None:
    item = _typed_gap_item(
        (("Stockholm", "Göteborg", "Malmö"), ("en",)),
        automatic_values=("stokholm",),
        excluded_automatic_values=("x",),
    )
    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.INLINE_CHOICE,
        rng=random.Random(1),
    )
    first, third = result.document.items[0].gaps
    assert _option_texts(first) == [
        ("choice_001", "Stockholm"),
        ("choice_002", "Göteborg"),
        ("choice_003", "Malmö"),
    ]
    assert first.correct_option_id == "choice_001"
    assert _option_texts(third) == [("choice_001", "en")]
    assert third.correct_option_id == "choice_001"
    for gap in (first, third):
        assert gap.accepted_values == ()
        assert gap.automatic_values == ()
        assert gap.excluded_automatic_values == ()
        for option in gap.options:
            paragraph = option.body[0]
            assert len(option.body) == 1 and paragraph.heading_level is None
            segment = paragraph.segments[0]
            assert len(paragraph.segments) == 1
            assert isinstance(segment, NativeTextSegment) and segment.marks == ()
    assert "accepted_values" not in result.dropped_content
    assert result.dropped_content == ()


def test_gap_fill_to_dropdown_keeps_other_drops_and_values_verbatim() -> None:
    payload = _typed_gap_item((("  Åsa är  ", "Ö"),)).model_dump()
    payload["ai_suggestion"] = {
        "gap_accepted_values": [{"gap_id": "gap_001", "accepted_values": ["Ö"]}],
        "fingerprint": "a" * 64,
        "provider_profile_id": "p",
        "model": "m",
        "prompt_template_version": "t",
    }
    item = NativeExamItem.model_validate(payload)
    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.INLINE_CHOICE,
        rng=random.Random(1),
    )
    gap = result.document.items[0].gaps[0]
    assert _option_texts(gap) == [("choice_001", "  Åsa är  "), ("choice_002", "Ö")]
    assert result.dropped_content == ("ai_suggestion",)


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        (NativeAnswerKeyOrigin.MACHINE_PROPOSED, NativeAnswerKeyOrigin.MACHINE_PROPOSED),
        (NativeAnswerKeyOrigin.SOURCE_PROVIDED, NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        (NativeAnswerKeyOrigin.TEACHER_AUTHORED, NativeAnswerKeyOrigin.TEACHER_AUTHORED),
        (NativeAnswerKeyOrigin.ABSENT, NativeAnswerKeyOrigin.TEACHER_AUTHORED),
    ],
)
def test_gap_fill_to_dropdown_key_origin(
    origin: NativeAnswerKeyOrigin, expected: NativeAnswerKeyOrigin
) -> None:
    absent = origin is NativeAnswerKeyOrigin.ABSENT
    item = make_gap_fill_item(origin=origin, accepted=() if absent else ("a", "b"))
    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.INLINE_CHOICE,
        rng=random.Random(1),
    )
    key = result.document.items[0].answer_key
    assert key.origin is expected
    assert key.correct_choice_ids == () and key.match_pairs == ()


def test_dropdown_to_gap_fill_still_drops_options_and_key() -> None:
    result = change_item_type(
        make_document(inline_choice_item()),
        item_id="item_001",
        target_kind=NativeExamItemKind.GAP_FILL,
        rng=random.Random(1),
    )
    assert set(result.dropped_content) == {"options", "correct_option_id"}
    assert result.document.items[0].gaps[0].options == ()


def test_gap_without_accepted_values_keeps_blank_option_pair_per_gap() -> None:
    # A validator allows empty accepted values only while the whole item has no key.
    item = _typed_gap_item(((), ()), origin=NativeAnswerKeyOrigin.ABSENT)
    result = change_item_type(
        make_document(item),
        item_id=item.item_id,
        target_kind=NativeExamItemKind.INLINE_CHOICE,
        rng=random.Random(1),
    )
    for gap in result.document.items[0].gaps:
        assert [(option.choice_id, option.body) for option in gap.options] == [
            ("choice_001", ()),
            ("choice_002", ()),
        ]
        assert gap.correct_option_id == "choice_001"
    assert result.document.items[0].answer_key.origin is NativeAnswerKeyOrigin.TEACHER_AUTHORED
