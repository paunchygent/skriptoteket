"""Instruction deletes retain only images referenced by surviving content or source."""

import hashlib
from collections.abc import Callable
from functools import partial

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent_commands import (
    delete_child,
    delete_parent,
    delete_parent_with_children,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetrySource,
)
from tests.unit.domain.curated_apps.exam_workspace.recorded_native_exam_support import (
    parent_over,
    recorded_document,
)

_ASSET_ID = "asset_00000000000000a1"
_DELETE_CASES = [
    pytest.param(delete_parent, False, id="heading-only"),
    pytest.param(delete_parent_with_children, False, id="cascade"),
    pytest.param(partial(delete_child, item_id="item_002"), True, id="last-child"),
]


def _source_image(item: NativeExamItem) -> NativeExamItem:
    # Explicitly synthetic source-only image, absent from the student body.
    source = NativeExamRetrySource(
        label_kind=item.kind,
        chunks=(
            NativeExamRetryChunk(
                anchor="body:0001",
                kind="drawing",
                text="",
                marked_text="",
                runs=(),
                paragraphs=(),
                images=(NativeExamRetryImage(asset_id=_ASSET_ID, offset=0, marked_offset=0),),
            ),
        ),
        owned_context_anchors=(),
        key_chunks=(),
        context_chunks=(),
    )
    return item.model_copy(update={"retry_source": source})


def _saved_exam(single_child: bool, reference: str) -> NativeExamDocument:
    base = recorded_document(
        (
            parent_over("parent_001", "First instruction", *((2,) if single_child else (2, 3, 4))),
            parent_over("parent_002", "Unchanged instruction", 6, 7),
        )
    )
    asset = NativeExamAsset(
        asset_id=_ASSET_ID,
        sha256=hashlib.sha256(b"synthetic-shared-picture").hexdigest(),
        media_type="image/png",
        byte_length=len(b"synthetic-shared-picture"),
    )
    paragraph = NativeParagraph(
        heading_level=None, segments=(NativeAssetSegment(asset_id=_ASSET_ID),)
    )
    parents = list(base.parents)
    parents[0] = parents[0].model_copy(update={"instruction": (*parents[0].instruction, paragraph)})
    items = list(base.items)
    if reference in {"child-body", "standalone-body", "child-source", "standalone-source"}:
        item = base.item_by_id("item_002" if reference.startswith("child-") else "item_001")
        item = (
            item.model_copy(update={"body": (*item.body, paragraph)})
            if reference.endswith("body")
            else _source_image(item)
        )
        items[item.sequence - 1] = item
    if reference == "other-parent-instruction":
        parents[1] = parents[1].model_copy(
            update={"instruction": (*parents[1].instruction, paragraph)}
        )
    data = dict(
        base.model_dump(),
        items=tuple(items),
        parents=tuple(parents),
        assets=(asset,),
        instructions=(paragraph,) if reference == "document-instruction" else (),
    )
    return parse_native_exam_document(
        native_exam_document_json_bytes(NativeExamDocument.model_validate(data))
    )


@pytest.mark.parametrize(("command", "single_child"), _DELETE_CASES)
@pytest.mark.parametrize(
    "reference",
    [
        "instruction-only",
        "child-body",
        "child-source",
        "standalone-body",
        "standalone-source",
        "other-parent-instruction",
        "document-instruction",
    ],
)
def test_parent_deletes_prune_instruction_assets_only_when_no_surviving_reference_exists(
    command: Callable[..., NativeExamDocument], single_child: bool, reference: str
) -> None:
    base = _saved_exam(single_child, reference)
    original = native_exam_document_json_bytes(base)

    result = command(base, parent_id="parent_001")

    # Deleting a part's last child keeps the part as a childless instruction block (G8), so
    # every instruction-held asset survives; removing the part itself prunes asset references
    # that only the removed part, its removed children or its own instruction held.
    keep_asset = single_child or (
        reference != "instruction-only"
        and (command is delete_parent or reference not in {"child-body", "child-source"})
    )
    # Deleting questions lowers each surviving part's stored place to the number of questions
    # left ahead of it; parent_002 keeps its own children in every case.
    part_child_ids = set(base.parents[1].item_ids)
    surviving_parent_002 = base.parents[1].model_copy(
        update={
            "place": next(item.sequence for item in result.items if item.item_id in part_child_ids)
            - 1
        }
    )
    expected_parents = (
        (base.parents[0].model_copy(update={"item_ids": ()}), surviving_parent_002)
        if single_child
        else (surviving_parent_002,)
    )
    assert result.assets == (base.assets if keep_asset else ())
    assert result.instructions == base.instructions
    assert result.parents == expected_parents
    assert native_exam_document_json_bytes(base) == original
    NativeExamDocument.model_validate(result.model_dump())
    assert [item.sequence for item in result.items] == list(range(1, len(result.items) + 1))
