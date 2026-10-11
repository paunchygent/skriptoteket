"""Matching items: native invariants, produced-item mapping and Exam.net export on a gold item."""

import re
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from scripts.exam_conversion_eval.gold import GoldExam, GoldItem
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMatchPair,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeGap,
    NativeMatchPair,
    native_export_blockers,
)

_GOLD = Path("tests/fixtures/exam_conversion/docx_corpus/gold")
_STEM = "bf26_english_1_unit_test_kap_1_2_med_facit"
_LABEL = "Vocabulary Matching, Question 1"
_ENTRY_LABEL = re.compile(r"^\s*(?:[A-Za-z]|\d{1,3})\s*[.)]\s+")


def _gold_item() -> GoldItem:
    exam = GoldExam.model_validate_json((_GOLD / f"{_STEM}.json").read_text())
    return next(item for item in exam.items if item.source_label == _LABEL)


def _table(item: GoldItem) -> tuple[list[str], list[str]]:
    """The gold prompt's two lists, labels removed, each in the order the source prints it."""
    rows = [line.split(" | ", 1) for line in item.prompt.split("\n") if " | " in line]
    return (
        [_ENTRY_LABEL.sub("", left) for left, _ in rows],
        [_ENTRY_LABEL.sub("", right) for _, right in rows],
    )


def _produced(
    *,
    pairs: tuple[tuple[str, str], ...] | None = None,
    left: tuple[str, ...] | None = None,
    right: tuple[str, ...] | None = None,
) -> ProducedItem:
    gold = _gold_item()
    lefts, rights = _table(gold)
    stems = [line for line in gold.prompt.split("\n") if " | " not in line]
    keyed = pairs if pairs is not None else tuple((p.left, p.right) for p in gold.pairs)
    return ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.MATCHING,
        title=None,
        body=tuple(
            ProducedParagraph(
                segments=(ProducedSegment(kind="text", text=line, accepted_values=(), hint=None),)
            )
            for line in stems
        ),
        points=gold.points if isinstance(gold.points, int) else None,
        choices=(),
        match_left=left if left is not None else tuple(lefts),
        match_right=right if right is not None else tuple(rights),
        match_pairs=tuple(ProducedMatchPair(left=a, right=b) for a, b in keyed),
    )


def _valid() -> NativeExamItem:
    return native_item(_produced())


def _with(item: NativeExamItem, **update: object) -> NativeExamItem:
    """Validate the item again with some fields replaced."""
    return NativeExamItem.model_validate({**dict(item), **update})


def _keyed(*pairs: tuple[str, str]) -> NativeAnswerKey:
    return NativeAnswerKey(
        origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
        match_pairs=tuple(NativeMatchPair(left_id=a, right_id=b) for a, b in pairs),
    )


def _document(item: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="t",
        items=(item,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def test_gold_item_is_a_keyed_matching_item_with_a_pair_for_every_entry():
    item = _gold_item()
    lefts, rights = _table(item)

    assert item.kind == "matching"
    assert len(item.pairs) == len(lefts) == len(rights) >= 2
    assert {p.left for p in item.pairs} == set(lefts)
    assert {p.right for p in item.pairs} == set(rights)


def test_valid_matching_item_validates_with_a_pair_per_entry():
    item = _valid()

    assert item.kind is NativeExamItemKind.MATCHING
    assert len(item.match_left) == 3
    assert len(item.match_right) == 3
    assert item.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED
    assert not item.choices
    assert not item.gaps
    assert native_export_blockers(_document(item)) == ()


def test_native_item_maps_each_produced_pair_to_the_ids_of_its_entries():
    gold = _gold_item()
    lefts, rights = _table(gold)

    item = _valid()

    assert [e.left_id for e in item.match_left] == ["left_001", "left_002", "left_003"]
    assert [e.right_id for e in item.match_right] == ["right_001", "right_002", "right_003"]
    assert [e.text for e in item.match_left] == lefts
    assert [e.text for e in item.match_right] == rights
    expected = [
        (f"left_{lefts.index(p.left) + 1:03d}", f"right_{rights.index(p.right) + 1:03d}")
        for p in gold.pairs
    ]
    assert [(p.left_id, p.right_id) for p in item.answer_key.match_pairs] == expected


def test_native_item_without_a_facit_leaves_the_matching_item_unkeyed_and_blocks_export():
    item = native_item(_produced(pairs=()))

    assert item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT
    assert item.answer_key.match_pairs == ()
    assert {b.reason for b in native_export_blockers(_document(item))} == {"missing_answer_key"}


@pytest.mark.parametrize("entry", ["left", "right"])
@pytest.mark.parametrize(
    "alter",
    [
        lambda text: text[:-1],
        lambda text: text[:-1] + ("x" if text[-1] != "x" else "y"),
        lambda text: text + " ",
        lambda text: text[0].swapcase() + text[1:],
    ],
    ids=["dropped_last", "replaced_last", "trailing_space", "first_case"],
)
def test_produced_pair_must_copy_its_entries_exactly(entry: str, alter):
    produced = _produced()
    pair = produced.match_pairs[0]
    altered = {"left": pair.left, "right": pair.right}
    altered[entry] = alter(altered[entry])
    assert altered[entry] != getattr(pair, entry)

    with pytest.raises(ValidationError, match="copies one match_left and one match_right entry"):
        produced.model_validate(
            {
                **produced.model_dump(),
                "match_pairs": [altered, *produced.model_dump()["match_pairs"][1:]],
            }
        )


def test_produced_pairs_that_use_one_right_entry_twice_fail_the_native_contract():
    gold = _gold_item()
    first, second, third = gold.pairs
    twice = ((first.left, first.right), (second.left, first.right), (third.left, third.right))

    with pytest.raises(ValidationError, match="pairs every right entry exactly once"):
        native_item(_produced(pairs=twice))


def test_right_entry_used_twice_leaves_another_right_entry_unpaired():
    item = _valid()
    pairs = item.answer_key.match_pairs
    reused = (pairs[0], pairs[1].model_copy(update={"right_id": pairs[0].right_id}), pairs[2])

    with pytest.raises(ValidationError, match="pairs every right entry exactly once"):
        _with(item, answer_key=item.answer_key.model_copy(update={"match_pairs": reused}))


def test_left_entry_without_a_pair_is_rejected():
    item = _valid()
    pairs = item.answer_key.match_pairs[:-1]

    with pytest.raises(ValidationError, match="pairs every left entry exactly once"):
        _with(item, answer_key=item.answer_key.model_copy(update={"match_pairs": pairs}))


def test_left_entry_paired_twice_is_rejected():
    item = _valid()
    first, second, third = item.answer_key.match_pairs
    doubled = (first, first.model_copy(update={"right_id": second.right_id}), third)

    with pytest.raises(ValidationError, match="pairs every left entry exactly once"):
        _with(item, answer_key=item.answer_key.model_copy(update={"match_pairs": doubled}))


@pytest.mark.parametrize(
    "undeclared",
    [("left_009", "right_001"), ("left_001", "right_009")],
    ids=["left", "right"],
)
def test_pair_naming_an_undeclared_entry_is_rejected(undeclared: tuple[str, str]):
    item = _valid()
    key = _keyed(undeclared, ("left_002", "right_002"), ("left_003", "right_003"))

    with pytest.raises(ValidationError, match="refer to declared entries"):
        _with(item, answer_key=key)


def test_pairs_on_a_single_choice_item_are_rejected():
    item = _valid()
    choices = (
        NativeChoice(choice_id="choice_001", text=item.match_right[0].text),
        NativeChoice(choice_id="choice_002", text=item.match_right[1].text),
    )
    key = _keyed(("left_001", "right_001")).model_copy(
        update={"correct_choice_ids": ("choice_001",)}
    )

    with pytest.raises(ValidationError, match="only matching items key match pairs"):
        _with(
            item,
            kind=NativeExamItemKind.SINGLE_CHOICE,
            match_left=(),
            match_right=(),
            choices=choices,
            answer_key=key,
        )


def test_pairs_on_a_free_text_item_are_rejected():
    item = _valid()
    key = _keyed(("left_001", "right_001")).model_copy(
        update={"origin": NativeAnswerKeyOrigin.NOT_APPLICABLE}
    )

    with pytest.raises(ValidationError, match="free_text items carry no answer-key data"):
        _with(
            item,
            kind=NativeExamItemKind.FREE_TEXT,
            match_left=(),
            match_right=(),
            answer_key=key,
        )


def test_match_lists_on_a_non_matching_kind_are_rejected():
    item = _valid()
    key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE)

    with pytest.raises(ValidationError, match="only matching items carry match lists"):
        _with(item, kind=NativeExamItemKind.FREE_TEXT, answer_key=key)


def test_choices_on_a_matching_item_are_rejected():
    item = _valid()
    choices = (
        NativeChoice(choice_id="choice_001", text=item.match_right[0].text),
        NativeChoice(choice_id="choice_002", text=item.match_right[1].text),
    )

    with pytest.raises(ValidationError, match="must not declare choices or gaps"):
        _with(item, choices=choices)


def test_gaps_on_a_matching_item_are_rejected():
    item = _valid()

    with pytest.raises(ValidationError, match="must not declare choices or gaps"):
        _with(item, gaps=(NativeGap(gap_id="gap_001", accepted_values=("x",)),))


def test_single_right_entry_is_rejected_even_when_every_left_entry_is_paired():
    item = _valid()
    key = _keyed(*(((p.left_id, "right_001")) for p in item.answer_key.match_pairs))

    with pytest.raises(ValidationError, match="at least two right entries"):
        _with(item, match_right=item.match_right[:1], answer_key=key)


def test_matching_item_without_left_entries_is_rejected():
    item = _valid()

    with pytest.raises(ValidationError, match="need left entries"):
        _with(item, match_left=(), answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT))


@pytest.mark.parametrize(
    ("origin", "message"),
    [
        (NativeAnswerKeyOrigin.ABSENT, "absent answer key must not carry key data"),
        (NativeAnswerKeyOrigin.NOT_APPLICABLE, "keyed item kinds cannot use not_applicable"),
    ],
)
def test_matching_key_origin_must_agree_with_its_pairs(origin: NativeAnswerKeyOrigin, message: str):
    item = _valid()

    with pytest.raises(ValidationError, match=message):
        _with(item, answer_key=item.answer_key.model_copy(update={"origin": origin}))


def test_duplicate_entry_ids_are_rejected():
    item = _valid()
    doubled = (item.match_left[0], item.match_left[0], item.match_left[2])

    with pytest.raises(ValidationError, match="match entry ids must be unique"):
        _with(item, match_left=doubled)


def test_qti_export_of_the_valid_item_is_an_automatic_matching_interaction_with_gold_pairs():
    gold = _gold_item()
    item = _valid()

    (qti,) = native_exam_to_examnet_qti_items(_document(item))

    assert qti.interaction_type is ExamNetQtiInteractionType.MATCHING
    assert qti.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC
    assert qti.max_score == gold.points
    assert [(p.left_text, p.right_text) for p in qti.match_pairs] == [
        (p.left, p.right) for p in gold.pairs
    ]
    assert [(p.left_identifier, p.right_identifier) for p in qti.match_pairs] == [
        (p.left_id, p.right_id) for p in item.answer_key.match_pairs
    ]
    assert not qti.choices
    assert not qti.text_entry_gaps


def test_qti_export_of_an_unkeyed_matching_item_carries_no_pairs():
    (qti,) = native_exam_to_examnet_qti_items(_document(native_item(_produced(pairs=()))))

    assert qti.interaction_type is ExamNetQtiInteractionType.MATCHING
    assert qti.match_pairs == ()
