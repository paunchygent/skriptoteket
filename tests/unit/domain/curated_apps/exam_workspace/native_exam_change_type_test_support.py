"""Shared fixtures for the native change-type matrix tests."""

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
    inline_choice_payload,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_single_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import matching_item

# Ordering has its own matrix in test_native_exam_ordering_rules.py.
KINDS = tuple(kind for kind in NativeExamItemKind if kind is not NativeExamItemKind.ORDERING)
CHOICE_KINDS = {NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE}
GAP_KINDS = {NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE}


def source_item(kind: NativeExamItemKind) -> NativeExamItem:
    """Independent fixtures with real key data, not copies of the conversion algorithm."""
    if kind is NativeExamItemKind.FREE_TEXT:
        return make_free_text_item()
    if kind is NativeExamItemKind.SINGLE_CHOICE:
        return make_single_choice_item()
    if kind is NativeExamItemKind.MULTIPLE_RESPONSE:
        payload = make_single_choice_item().model_dump()
        payload["kind"] = kind
        payload["answer_key"]["correct_choice_ids"] = ("choice_001", "choice_002")
        return NativeExamItem.model_validate(payload)
    if kind is NativeExamItemKind.GAP_FILL:
        return make_gap_fill_item(accepted=("NF", "nominalfras"), automatic=("nf",))
    if kind is NativeExamItemKind.INLINE_CHOICE:
        return inline_choice_item(points=2)
    return matching_item()


def expected_dropped(source: NativeExamItem, target: NativeExamItemKind) -> set[str]:
    """What the target cannot represent, specified independently of production output."""
    if source.kind is target:
        return set()
    dropped: set[str] = set()
    if source.kind in CHOICE_KINDS:
        if target not in CHOICE_KINDS:
            dropped.update(("choices", "correct_choice_ids"))
        elif (
            target is NativeExamItemKind.SINGLE_CHOICE
            and len(source.answer_key.correct_choice_ids) > 1
        ):
            dropped.add("correct_choice_ids")
    if source.kind in GAP_KINDS:
        if target not in GAP_KINDS:
            dropped.add("gaps")
        if source.kind is NativeExamItemKind.GAP_FILL:
            if target is not NativeExamItemKind.INLINE_CHOICE:
                dropped.add("accepted_values")
        else:
            dropped.update(("options", "correct_option_id"))
    if source.kind is NativeExamItemKind.MATCHING:
        dropped.update(("match_left", "match_right", "match_pairs", "tick_points"))
    return dropped


def gap_fill_with_kept_word() -> NativeExamItem:
    """One live gap plus one reverted answer word linked to a kept gap.

    Mirrors the production revert shape: the answered gap leaves ``gaps``,
    its word stays visible with the kept id link, and its full record rides
    in ``kept_gaps`` under that id.
    """
    base = make_gap_fill_item(accepted=("Svar",))
    data = base.model_dump(mode="json")
    data["body"][0]["segments"].append(
        {"kind": "text", "text": " NF", "marks": ["bold"], "kept_gap_id": "gap_002"}
    )
    kept = make_gap_fill_item(accepted=("NF", "nominalfras")).gaps[0].model_dump(mode="json")
    kept["gap_id"] = "gap_002"
    data["kept_gaps"] = [kept]
    return NativeExamItem.model_validate(data)


def inline_choice_with_kept_word() -> NativeExamItem:
    """One live dropdown gap plus one reverted word linked to a kept dropdown gap."""
    payload = inline_choice_payload()
    live = [gap for gap in payload["gaps"] if gap["gap_id"] == "gap_001"]
    kept = [gap for gap in payload["gaps"] if gap["gap_id"] == "gap_002"]
    assert len(live) == 1 and len(kept) == 1
    kept_record = dict(kept[0])
    kept_record["gap_id"] = "gap_003"
    word = "".join(
        segment["text"]
        for option in kept_record["options"]
        if option["choice_id"] == kept_record["correct_option_id"]
        for paragraph in option["body"]
        for segment in paragraph["segments"]
    )
    assert word
    payload["gaps"] = live
    payload["kept_gaps"] = [kept_record]
    payload["body"][0]["segments"] = [
        (
            {"kind": "text", "text": word, "marks": [], "kept_gap_id": "gap_003"}
            if segment.get("kind") == "gap" and segment.get("gap_id") == "gap_002"
            else segment
        )
        for segment in payload["body"][0]["segments"]
    ]
    return NativeExamItem.model_validate(payload)
