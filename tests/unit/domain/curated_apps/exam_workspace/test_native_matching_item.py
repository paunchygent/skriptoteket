"""Gold matching items: produced-item mapping, DOCX rendering and Exam.net export."""

import io
from decimal import Decimal

import pytest
from docx import Document as DocxDocument
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_writer,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    DISTRACTOR_TEXT,
    gold_item,
    gold_lists,
    produced_item,
    single_item_document,
    valid_item,
    with_distractor,
)


def test_gold_item_is_a_keyed_matching_item_with_a_pair_for_every_entry():
    item = gold_item()
    lefts, rights = gold_lists(item)

    assert item.kind == "matching"
    assert len(item.pairs) == len(lefts) == len(rights) >= 2
    assert {p.left for p in item.pairs} == set(lefts)
    assert {p.right for p in item.pairs} == set(rights)


def test_produced_pairs_that_use_one_right_entry_twice_are_a_valid_grid():
    gold = gold_item()
    first, second, third = gold.pairs
    twice = ((first.left, first.right), (second.left, first.right), (third.left, third.right))

    item = aligned_native_item(produced_item(pairs=twice), language="sv", foreign_chunks=()).item

    right_id = item.answer_key.match_pairs[0].right_id
    assert [p.left_id for p in item.answer_key.match_pairs if p.right_id == right_id] == [
        "left_001",
        "left_002",
    ]


def test_native_item_maps_each_produced_pair_to_the_ids_of_its_entries():
    gold = gold_item()
    lefts, rights = gold_lists(gold)

    item = valid_item()

    assert [e.left_id for e in item.match_left] == ["left_001", "left_002", "left_003"]
    assert [e.right_id for e in item.match_right] == ["right_001", "right_002", "right_003"]
    assert [body_plain_text(e.body) for e in item.match_left] == lefts
    assert [body_plain_text(e.body) for e in item.match_right] == rights
    expected = [
        (f"left_{lefts.index(p.left) + 1:03d}", f"right_{rights.index(p.right) + 1:03d}")
        for p in gold.pairs
    ]
    assert [(p.left_id, p.right_id) for p in item.answer_key.match_pairs] == expected


def test_native_item_without_a_facit_leaves_the_matching_item_unkeyed_and_blocks_export():
    item = aligned_native_item(produced_item(pairs=()), language="sv", foreign_chunks=()).item

    assert item.answer_key.origin is NativeAnswerKeyOrigin.ABSENT
    assert item.answer_key.match_pairs == ()
    assert item.tick_points == Decimal(1)
    assert item.points is None
    assert {b.reason for b in native_export_blockers(single_item_document(item))} == {
        "missing_answer_key",
        "missing_points",
    }


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
    produced = produced_item()
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


def test_distractors_are_listed_by_the_docx_writer_and_stay_out_of_its_pairs():
    item = with_distractor(valid_item())

    content = exam_workspace_docx_writer.ExamWorkspaceDocxWriter().build_docx_bytes(
        single_item_document(item)
    )

    texts = [paragraph.text for paragraph in DocxDocument(io.BytesIO(content)).paragraphs]
    pair = f"{SWEDISH_EXAM_LABELS.pair}:"
    assert f"D) {DISTRACTOR_TEXT}" in texts
    assert not [t for t in texts if t.startswith(pair) and DISTRACTOR_TEXT in t]
    assert len([t for t in texts if t.startswith(pair)]) == len(item.answer_key.match_pairs)


def test_qti_export_of_the_valid_item_is_an_automatic_matching_interaction_with_gold_pairs():
    gold = gold_item()
    item = valid_item()

    (qti,) = native_exam_to_examnet_qti_items(single_item_document(item))

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
    (qti,) = native_exam_to_examnet_qti_items(
        single_item_document(
            aligned_native_item(produced_item(pairs=()), language="sv", foreign_chunks=()).item
        )
    )

    assert qti.interaction_type is ExamNetQtiInteractionType.MATCHING
    assert qti.match_pairs == ()
