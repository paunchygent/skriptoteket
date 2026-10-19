"""Score round trips through the real QTI package bytes (review 596c1654 F4/F5).

F5: a present zero stays zero, including a zero-point matching grid.
F4: a parent gap child's score comes only from exact evidence (the parent
remainder); anything the package does not state exactly goes to review with
the named Swedish reason instead of being guessed.
"""

from __future__ import annotations

import io
import zipfile
from decimal import Decimal
from xml.etree import ElementTree

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_terms import (
    QTI_NAMESPACE,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
)
from tests.unit.application.curated_apps.test_exam_workspace_qti_round_trip import (
    _document,
    _parse_handler,
    _round_trip,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_paragraph,
    make_review,
    make_single_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)

_MISSING_POINTS_REASON = "Poängen stod inte i paketet. Ange poäng."


def _gap_child(
    *, sequence: int, item_id: str, points: int | float, gap_count: int
) -> NativeExamItem:
    segments: list[NativeTextSegment | NativeGapSegment] = []
    gaps: list[NativeGap] = []
    for index in range(1, gap_count + 1):
        segments.append(NativeTextSegment(text=f"Frastyp {index}: ", marks=()))
        segments.append(NativeGapSegment(gap_id=f"gap_{index:03d}"))
        gaps.append(NativeGap(gap_id=f"gap_{index:03d}", accepted_values=(f"NF{index}",)))
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.GAP_FILL,
        body=(NativeParagraph(heading_level=None, segments=tuple(segments)),),
        points=points,
        gaps=tuple(gaps),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=make_review(),
    )


def _parent(children: tuple[NativeExamItem, ...]) -> NativeExamParent:
    return NativeExamParent(
        parent_id="parent_001",
        place=min(child.sequence for child in children) - 1,
        instruction=(make_paragraph("Gör alla deluppgifter."),),
        item_ids=tuple(child.item_id for child in children),
    )


def test_zero_point_items_keep_their_points() -> None:
    choice = make_single_choice_item()
    gap = make_gap_fill_item().model_copy(
        update={"points": 0, "item_id": "item_002", "sequence": 2}
    )
    free_text = make_free_text_item().model_copy(
        update={"points": 0, "item_id": "item_003", "sequence": 3}
    )
    choice = choice.model_copy(update={"points": 0})
    document = _document((choice, gap, free_text))

    _, container = _round_trip(document)

    assert [item.points for item in container.document.items] == [0, 0, 0]
    assert container.notes == ()


def test_zero_point_matching_grid_keeps_its_pairs_and_tick_points() -> None:
    grid = matching_item(tick_points=Decimal("0"), points=0)
    choice = make_single_choice_item(sequence=2, item_id="item_002")
    document = _document((grid, choice))

    _, container = _round_trip(document)

    assert [item.kind for item in container.document.items] == [
        NativeExamItemKind.MATCHING,
        NativeExamItemKind.SINGLE_CHOICE,
    ]
    imported_grid = container.document.items[0]
    assert imported_grid.points == 0
    assert imported_grid.tick_points == Decimal("0.00")
    assert len(imported_grid.answer_key.match_pairs) == 3
    assert container.notes == ()


def test_package_with_only_a_zero_point_matching_grid_imports() -> None:
    grid = matching_item(tick_points=Decimal("0"), points=0)
    document = _document((grid,))

    _, container = _round_trip(document)

    assert len(container.document.items) == 1
    assert container.document.items[0].points == 0
    assert container.document.items[0].tick_points == Decimal("0.00")


@pytest.mark.parametrize("points", [0.99, 1, 1.01])
def test_parent_gap_child_keeps_its_exact_score(points: float) -> None:
    gap = _gap_child(sequence=1, item_id="item_001", points=points, gap_count=3)
    other = make_single_choice_item(sequence=2, item_id="item_002")
    document = _document((gap, other), parents=(_parent((gap, other)),))

    _, container = _round_trip(document)

    assert container.notes == ()
    assert container.document.items[0].points == points
    assert container.document.items[1].points == 1
    assert container.document.items[0].review.state is NativeItemReviewState.REVIEW_COMPLETE


def test_parent_gap_children_without_stated_scores_go_to_review() -> None:
    first = _gap_child(sequence=1, item_id="item_001", points=2, gap_count=2)
    second = _gap_child(sequence=2, item_id="item_002", points=3, gap_count=1)
    document = _document((first, second), parents=(_parent((first, second)),))

    _, container = _round_trip(document)

    assert [item.points for item in container.document.items] == [None, None]
    for item in container.document.items:
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        assert _MISSING_POINTS_REASON in item.review.reasons
    assert sum(item.points or 0 for item in container.document.items) == 0


def test_inconsistent_remainder_leaves_the_gap_child_without_points() -> None:
    gap = _gap_child(sequence=1, item_id="item_001", points=1, gap_count=3)
    other = make_single_choice_item(sequence=2, item_id="item_002")
    document = _document((gap, other), parents=(_parent((gap, other)),))

    package, _ = _round_trip(document)
    tampered = _replace_parent_maxscore(package, "999")
    container = _parse_handler().handle(filename="paket.zip", content=tampered, course_key=None)

    assert container.document.items[0].points is None
    assert container.document.items[0].review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert _MISSING_POINTS_REASON in container.document.items[0].review.reasons
    assert container.document.items[1].points == 1


def _replace_parent_maxscore(package: bytes, value: str) -> bytes:
    out = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(package)) as src,
        zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as dst,
    ):
        for info in src.infolist():
            payload = src.read(info)
            if info.filename.startswith("items/") and info.filename.endswith(".xml"):
                root = ElementTree.fromstring(payload)
                namespace = f"{{{QTI_NAMESPACE}}}"
                for outcome in root.findall(f"{namespace}qti-outcome-declaration"):
                    if outcome.get("identifier") == "MAXSCORE":
                        value_element = outcome.find(
                            f"{namespace}qti-default-value/{namespace}qti-value"
                        )
                        if value_element is not None:
                            value_element.text = value
                ElementTree.indent(root, space="  ")
                payload = ElementTree.tostring(root, encoding="utf-8")
            dst.writestr(info.filename, payload)
    return out.getvalue()
