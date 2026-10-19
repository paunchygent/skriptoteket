"""Round-trip tests for the QTI parent item reader.

Purpose:
    Prove that `examnet_qti_item_reader` inverts the writer's shared-instruction
    layout: a parent item reads back as one item whose children carry their own
    interaction, prompt, points, keys and image indexes.

Relationships:
    - Builds native documents with parents using the existing exam-workspace
      builders and exports them through `native_exam_to_examnet_qti_items`.
    - Split from the oversized parent-reader module; shared builders live in
      `examnet_qti_reader_test_support` and are imported, never copied.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    child_projection as _child_projection,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    imaged_choice as _imaged_choice,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    make_asset as _asset,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_document as _document,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_export as _export,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_gap_fill_child as _gap_fill_child,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_of as _parent,
)
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_reader_test_support import (
    parent_round_trip as _round_trip,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_gap_fill_item,
    make_single_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_matching_test_support import (
    matching_item,
)

pytestmark = pytest.mark.unit

_PNG_A = b"\x89PNG\r\n\x1a\npayload-a"
_PNG_B = b"\x89PNG\r\n\x1a\npayload-b"
_PNG_C = b"\x89PNG\r\n\x1a\npayload-c"


def _image_payloads(item: ExamNetQtiItem) -> tuple[tuple[str, bytes], ...]:
    return tuple((image.media_type, image.payload) for image in item.image_resources)


def _image_indexes(paragraphs: tuple[ExamNetQtiPromptParagraph, ...]) -> list[int]:
    return [
        segment.image_index
        for paragraph in paragraphs
        for segment in paragraph.segments
        if isinstance(segment, ExamNetQtiPromptImage)
    ]


# --- the mixed parent --------------------------------------------------------------------


def test_a_mixed_parent_reads_back_every_child_and_the_shared_instruction() -> None:
    children = (
        make_single_choice_item(sequence=1, item_id="item_001"),
        make_gap_fill_item(sequence=2, item_id="item_002"),
        make_free_text_item(sequence=3, item_id="item_003"),
        inline_choice_item(sequence=4, points=2),
    )
    (exported,) = _export(_document(children, parent=_parent(children)), assets_by_id={})

    read = _round_trip((exported,))

    assert len(read) == 1
    (parent,) = read
    assert isinstance(parent, ExamNetQtiItem)
    assert parent.item_id == "parent_001"
    assert parent.sequence == 1
    assert parent.interaction_type is exported.interaction_type
    assert parent.title == exported.title
    assert parent.prompt_paragraphs == exported.prompt_paragraphs
    assert parent.instruction_lines == exported.instruction_lines
    assert parent.max_score == exported.max_score == 9
    assert parent.evaluation_mode is ExamNetQtiEvaluationMode.AUTOMATIC
    assert len(parent.children) == len(exported.children) == 4
    for export_child, read_child in zip(exported.children, parent.children, strict=True):
        assert read_child.item_id == f"parent_001_child_{read_child.sequence}"
    # Review 596c1654 F4: the rounded per-gap share states no total, so the two
    # gap children keep None for the mapper's review loss; the block children
    # still invert exactly.
    assert [child.max_score for child in parent.children] == [1, None, 4, None]
    assert _child_projection(parent.children[0]) == _child_projection(exported.children[0])
    assert _child_projection(parent.children[2]) == _child_projection(exported.children[2])


def test_a_matching_child_round_trips_its_lists_and_pairs() -> None:
    children = (
        make_single_choice_item(sequence=1, item_id="item_001"),
        matching_item(sequence=2, item_id="item_002"),
    )
    (exported,) = _export(_document(children, parent=_parent(children)), assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert len(parent.children) == 2
    assert parent.children[1].max_score == 3
    assert _child_projection(parent.children[1]) == _child_projection(exported.children[1])


def test_a_parent_with_only_a_gap_fill_child_reads_as_one_separator_child() -> None:
    child = _gap_fill_child(sequence=1, item_id="item_001", points=2, gap_count=1)
    document = _document((child,), parent=_parent((child,)))
    (exported,) = _export(document, assets_by_id={})

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert len(parent.children) == 1
    (read_child,) = parent.children
    assert read_child.interaction_type is ExamNetQtiInteractionType.GAP_FILL
    assert read_child.max_score == 2
    assert _child_projection(read_child) == _child_projection(exported.children[0])


def test_instruction_and_child_pictures_keep_their_own_indexes() -> None:
    payloads = {
        "asset_00000000000000a1": _PNG_A,
        "asset_00000000000000b2": _PNG_B,
        "asset_00000000000000c3": _PNG_C,
    }
    assets = tuple(_asset(asset_id, payload, "image/png") for asset_id, payload in payloads.items())
    stem_asset, first_asset, second_asset = payloads
    children = (
        _imaged_choice(sequence=1, item_id="item_001", asset_id=first_asset),
        _imaged_choice(sequence=2, item_id="item_002", asset_id=second_asset),
    )
    instruction = NativeExamParent(
        parent_id="parent_001",
        place=children[0].sequence - 1,
        instruction=(
            NativeParagraph(
                heading_level=None,
                segments=(
                    NativeTextSegment(text="Se bilden: ", marks=()),
                    NativeAssetSegment(asset_id=stem_asset),
                ),
            ),
        ),
        item_ids=tuple(child.item_id for child in children),
    )
    document = _document(children, parent=instruction, assets=assets)
    (exported,) = _export(document, assets_by_id=payloads)

    (parent,) = _round_trip((exported,))

    assert isinstance(parent, ExamNetQtiItem)
    assert _image_payloads(parent) == _image_payloads(exported)
    assert parent.image_resources[0].payload == _PNG_A
    assert parent.children[0].image_resources[0].payload == _PNG_B
    assert parent.children[1].image_resources[0].payload == _PNG_C
    # every prompt image index addresses the item's own resources from zero
    assert _image_indexes(parent.prompt_paragraphs) == [0]
    assert _image_indexes(parent.children[0].prompt_paragraphs) == [0]
    assert _image_indexes(parent.children[1].prompt_paragraphs) == [0]
    assert _child_projection(parent.children[0]) == _child_projection(exported.children[0])
    assert _child_projection(parent.children[1]) == _child_projection(exported.children[1])
