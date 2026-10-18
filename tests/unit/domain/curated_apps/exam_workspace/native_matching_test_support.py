"""Shared builders for native matching-item tests: the recorded gold grid and generic grids."""

import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from scripts.exam_conversion_eval.gold import GoldExam, GoldItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMatchPair,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import plain_body

_GOLD_DIR = Path("tests/fixtures/exam_conversion/docx_corpus/gold")
_GOLD_STEM = "bf26_english_1_unit_test_kap_1_2_med_facit"
_GOLD_LABEL = "Vocabulary Matching, Question 1"
_ENTRY_LABEL = re.compile(r"^\s*(?:[A-Za-z]|\d{1,3})\s*[.)]\s+")

DISTRACTOR_TEXT = "an entry no left entry matches"

_MATCH_RIGHT_TEXT = {
    "right_001": "däggdjur",
    "right_002": "fåglar",
    "right_003": "fiskar",
    "right_004": "kräldjur",
}


def _review() -> NativeItemReview:
    return NativeItemReview(
        state=NativeItemReviewState.REVIEW_COMPLETE,
        parse_origin=NativeParseOrigin.DETERMINISTIC,
        confidence=0.9,
    )


def _paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),))


def gold_item() -> GoldItem:
    exam = GoldExam.model_validate_json((_GOLD_DIR / f"{_GOLD_STEM}.json").read_text())
    return next(item for item in exam.questions if item.source_label == _GOLD_LABEL)


def gold_lists(item: GoldItem) -> tuple[list[str], list[str]]:
    """The gold prompt's two lists, labels removed, each in the order the source prints it."""
    rows = [line.split(" | ", 1) for line in item.prompt.split("\n") if " | " in line]
    return (
        [_ENTRY_LABEL.sub("", left) for left, _ in rows],
        [_ENTRY_LABEL.sub("", right) for _, right in rows],
    )


def produced_item(
    *,
    pairs: tuple[tuple[str, str], ...] | None = None,
    left: tuple[str, ...] | None = None,
    right: tuple[str, ...] | None = None,
) -> ProducedItem:
    gold = gold_item()
    lefts, rights = gold_lists(gold)
    stems = [line for line in gold.prompt.split("\n") if " | " not in line]
    keyed = pairs if pairs is not None else tuple((p.left, p.right) for p in gold.pairs)
    return ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.MATCHING,
        key_source="copied" if keyed else None,
        facit_text="Correct answer: 1–B, 2–A, 3–C" if keyed else None,
        body=tuple(
            ProducedParagraph(
                segments=(
                    ProducedSegment(
                        kind="text",
                        text=line,
                        accepted_values=(),
                    ),
                )
            )
            for line in stems
        ),
        points=gold.points if isinstance(gold.points, int) else None,
        choices=(),
        match_left=left if left is not None else tuple(lefts),
        match_right=right if right is not None else tuple(rights),
        match_pairs=tuple(ProducedMatchPair(left=a, right=b) for a, b in keyed),
    )


def valid_item() -> NativeExamItem:
    return aligned_native_item(produced_item(), language="sv").item


def with_update(item: NativeExamItem, **update: object) -> NativeExamItem:
    """Validate the item again with some fields replaced."""
    return NativeExamItem.model_validate({**dict(item), **update})


def keyed_answer(*pairs: tuple[str, str]) -> NativeAnswerKey:
    return NativeAnswerKey(
        origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
        match_pairs=tuple(NativeMatchPair(left_id=a, right_id=b) for a, b in pairs),
    )


def with_distractor(item: NativeExamItem) -> NativeExamItem:
    extra = NativeMatchRight(
        right_id=f"right_{len(item.match_right) + 1:03d}",
        body=plain_body(DISTRACTOR_TEXT),
    )
    return with_update(item, match_right=(*item.match_right, extra))


def single_item_document(item: NativeExamItem) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="t",
        items=(item,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def matching_item(
    *,
    sequence: int = 1,
    item_id: str = "item_001",
    pairs: tuple[tuple[str, str], ...] = (
        ("left_001", "right_001"),
        ("left_002", "right_002"),
        ("left_003", "right_003"),
    ),
    match_right: tuple[str, ...] = ("right_001", "right_002", "right_003"),
    tick_points: Decimal | None = Decimal("1"),
    points: int | float | None = 3,
    origin: NativeAnswerKeyOrigin = NativeAnswerKeyOrigin.SOURCE_PROVIDED,
) -> NativeExamItem:
    """A hand-built matching grid, independent of the gold example."""
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.MATCHING,
        body=(_paragraph("Kategorisera orden i rätt ordklass."),),
        points=points,
        tick_points=tick_points,
        match_left=(
            NativeMatchLeft(left_id="left_001", body=plain_body("hund")),
            NativeMatchLeft(left_id="left_002", body=plain_body("katt")),
            NativeMatchLeft(left_id="left_003", body=plain_body("fågel")),
        ),
        match_right=tuple(
            NativeMatchRight(right_id=right_id, body=plain_body(_MATCH_RIGHT_TEXT[right_id]))
            for right_id in match_right
        ),
        answer_key=NativeAnswerKey(
            origin=origin,
            match_pairs=tuple(
                NativeMatchPair(left_id=left_id, right_id=right_id) for left_id, right_id in pairs
            ),
        ),
        review=_review(),
    )
