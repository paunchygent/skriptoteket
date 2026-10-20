"""Retyping to gap_fill places the new gap at the end of the last question paragraph.

Shared case table with the frontend Vitest spec:
``tests/fixtures/exam_workspace/gap_text_placement_cases.json``. The rule mirrors
the client's ``withGapTextShape``: trailing empty paragraphs drop, then the gap
is appended to the last remaining paragraph with a single unmarked ``" "``
separator unless that paragraph already ends in whitespace or in a non-text
segment. An empty question yields a lone gap paragraph followed by an empty
paragraph. ``inline_choice`` retypes keep the historic own-paragraph placement.
"""

import json
import random
from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import change_item_type
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeItemReview
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)

_CASES_PATH = (
    Path(__file__).resolve().parents[4]
    / "fixtures"
    / "exam_workspace"
    / "gap_text_placement_cases.json"
)


def _load_cases() -> list[dict[str, object]]:
    payload = json.loads(_CASES_PATH.read_text())
    cases = payload["cases"]
    assert isinstance(cases, list) and cases
    return cases


def _paragraphs(raw: object) -> tuple[NativeParagraph, ...]:
    assert isinstance(raw, list)
    return tuple(NativeParagraph.model_validate(entry) for entry in raw)


def _fallback_item(body: tuple[NativeParagraph, ...]) -> NativeExamItem:
    return make_free_text_item().model_copy(
        update={
            "body": body,
            "review": NativeItemReview(
                state=NativeItemReviewState.REVIEW_REQUIRED,
                parse_origin=NativeParseOrigin.SOURCE_FALLBACK,
            ),
        }
    )


def _document_for(item: NativeExamItem) -> NativeExamDocument:
    """A document declaring the picture assets the question body references."""
    asset_ids = sorted(
        {
            segment.asset_id
            for paragraph in item.body
            for segment in paragraph.segments
            if isinstance(segment, NativeAssetSegment)
        }
    )
    if not asset_ids:
        return make_document(item)
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(item,),
        assets=tuple(
            NativeExamAsset(
                asset_id=asset_id,
                sha256="a" * 64,
                media_type="image/png",
                byte_length=10,
            )
            for asset_id in asset_ids
        ),
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _is_short_answer_shape(item: NativeExamItem) -> bool:
    """One gap alone in the last paragraph, mirroring the client's shape rule."""
    if item.kind is not NativeExamItemKind.GAP_FILL or len(item.gaps) != 1:
        return False
    placed = [
        segment.gap_id
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeGapSegment)
    ]
    if placed != [item.gaps[0].gap_id]:
        return False
    if not item.body:
        return False
    last = item.body[-1]
    return (
        len(last.segments) == 1
        and isinstance(last.segments[0], NativeGapSegment)
        and last.segments[0].gap_id == item.gaps[0].gap_id
    )


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: str(case["name"]))
def test_gap_fill_retype_places_gap_by_shared_rule(case: dict[str, object]) -> None:
    question = _paragraphs(case["question"])
    expected = _paragraphs(case["expected"])

    result = change_item_type(
        _document_for(_fallback_item(question)),
        item_id="item_001",
        target_kind=NativeExamItemKind.GAP_FILL,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    assert changed.kind is NativeExamItemKind.GAP_FILL
    assert changed.body == expected
    assert [gap.gap_id for gap in changed.gaps] == ["gap_001"]
    assert changed.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert changed.review.parse_origin is NativeParseOrigin.TEACHER_CREATED
    # The gap must not stand alone in the last paragraph: the editor shows the
    # Lucktext gap tools instead of the Kort svar field. An empty question also
    # avoids the shape, since its gap paragraph is followed by an empty one.
    assert not _is_short_answer_shape(changed)


def test_staging_lucktext_retype_is_not_kort_svar() -> None:
    """Staging fråga 3a: choosing Lucktext must show the gap tools at once (D9)."""
    question = _paragraphs(
        [
            {
                "segments": [
                    {
                        "kind": "text",
                        "text": "Ange bisatsens typ",
                        "marks": [],
                        "kept_gap_id": None,
                    }
                ],
                "heading_level": None,
            }
        ]
    )

    result = change_item_type(
        _document_for(_fallback_item(question)),
        item_id="item_001",
        target_kind=NativeExamItemKind.GAP_FILL,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    last = changed.body[-1]
    assert isinstance(last.segments[-1], NativeGapSegment)
    assert len(last.segments) > 1
    assert not _is_short_answer_shape(changed)


def test_inline_choice_retype_keeps_own_gap_paragraph() -> None:
    question = _paragraphs(
        [
            {
                "segments": [
                    {
                        "kind": "text",
                        "text": "Välj rätt alternativ.",
                        "marks": [],
                        "kept_gap_id": None,
                    }
                ],
                "heading_level": None,
            }
        ]
    )

    result = change_item_type(
        _document_for(_fallback_item(question)),
        item_id="item_001",
        target_kind=NativeExamItemKind.INLINE_CHOICE,
        rng=random.Random(1),
    )

    changed = result.document.items[0]
    assert changed.kind is NativeExamItemKind.INLINE_CHOICE
    assert changed.body[:-1] == question
    last = changed.body[-1]
    assert len(last.segments) == 1
    assert isinstance(last.segments[0], NativeGapSegment)
    assert last.segments[0].gap_id == "gap_001"
    assert changed.review.parse_origin is NativeParseOrigin.TEACHER_CREATED
