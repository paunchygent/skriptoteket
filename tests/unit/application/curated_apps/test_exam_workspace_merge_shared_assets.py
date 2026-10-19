"""F2b: a progressive merge keeps pictures only shared instruction bodies reference.

A valid native document may place a picture in the document's global instructions or a
parent's instruction and in no item body or retry source. The merge derives the retained
asset set from the selected instructions and parents, so a no-op merge keeps such a
picture and a delivered parent's picture, while an asset no selected body references is
still pruned.
"""

from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    CandidateUnit,
    ConversionMerge,
    ConversionProgress,
    ConversionTarget,
    ConversionUnitState,
    merge_conversion,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge_fields import (
    digest_json,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import (
    NativeExamParent,
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
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_asset_ids

_DOCUMENT_ID = UUID("00000000-0000-4000-8000-000000000039")
_STEM_TEXT = "Del 2: Satsdelar"
_NEW_INSTRUCTION = (
    NativeParagraph(
        heading_level=None, segments=(NativeTextSegment(text="Ny instruktion.", marks=()),)
    ),
)


def _asset(name: str, payload: bytes = b"shared-diagram") -> NativeExamAsset:
    return NativeExamAsset(
        asset_id="asset_" + name * 16,
        sha256=sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )


def _free_text(item_id: str, sequence: int, text: str) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        writing_lines=8,
        body=(
            NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),
        ),
        points=1,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
    )


def _stem(asset_id: str) -> tuple[NativeParagraph, ...]:
    return (
        NativeParagraph(
            heading_level=None,
            segments=(
                NativeTextSegment(text=_STEM_TEXT, marks=()),
                NativeAssetSegment(asset_id=asset_id),
            ),
        ),
    )


def _document(
    *,
    items: tuple[NativeExamItem, ...],
    instructions: tuple[NativeParagraph, ...] = (),
    parents: tuple[NativeExamParent, ...] = (),
    assets: tuple[NativeExamAsset, ...] = (),
) -> NativeExamDocument:
    """A saved head the native contract admits, so every fixture is valid before merging."""
    return NativeExamDocument(
        document_id=_DOCUMENT_ID,
        revision=1,
        title="Prov",
        instructions=instructions,
        items=items,
        parents=parents,
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _instructions_digest(body: tuple[NativeParagraph, ...]) -> str:
    return digest_json([paragraph.model_dump(mode="json") for paragraph in body])


def _no_op_merge(head: NativeExamDocument) -> ConversionMerge:
    return merge_conversion(
        head=head, progress=ConversionProgress(), target=ConversionTarget(units=())
    )


def test_no_op_merge_keeps_a_picture_only_the_global_instruction_references() -> None:
    asset = _asset("a")
    head = _document(
        items=(_free_text("item_001", 1, "Fråga ett"), _free_text("item_002", 2, "Fråga två")),
        instructions=_stem(asset.asset_id),
        assets=(asset,),
    )
    assert all(item.body_asset_ids() == () for item in head.items)
    assert all(item.source_asset_ids() == () for item in head.items)

    merged = _no_op_merge(head)

    assert merged.document.instructions == head.instructions
    assert body_asset_ids(merged.document.instructions) == (asset.asset_id,)
    assert merged.document.assets == (asset,)


def test_no_op_merge_keeps_a_picture_only_a_parent_instruction_references() -> None:
    asset = _asset("b")
    items = (_free_text("item_001", 1, "Fråga ett"), _free_text("item_002", 2, "Fråga två"))
    head = _document(
        items=items,
        parents=(
            NativeExamParent(
                parent_id="parent_001",
                place=items[0].sequence - 1,
                instruction=_stem(asset.asset_id),
                item_ids=tuple(item.item_id for item in items),
            ),
        ),
        assets=(asset,),
    )
    assert all(item.body_asset_ids() == () for item in head.items)

    merged = _no_op_merge(head)

    assert merged.document.parents == head.parents
    assert body_asset_ids(merged.document.parents[0].instruction) == (asset.asset_id,)
    assert merged.document.assets == (asset,)


def test_edited_shared_instructions_keep_their_picture_against_a_new_proposal() -> None:
    asset = _asset("c")
    head = _document(
        items=(_free_text("item_001", 1, "Fråga ett"),),
        instructions=_stem(asset.asset_id),
        assets=(asset,),
    )
    # The teacher's instruction no longer matches what conversion last delivered, so the
    # conversion's new proposal must not replace it — or its picture.
    progress = ConversionProgress(
        instructions_digest=_instructions_digest(
            (
                NativeParagraph(
                    heading_level=None,
                    segments=(NativeTextSegment(text="Tidigare instruktion.", marks=()),),
                ),
            )
        )
    )

    merged = merge_conversion(
        head=head,
        progress=progress,
        target=ConversionTarget(units=(), instructions=_NEW_INSTRUCTION),
    )

    assert merged.document.instructions == head.instructions
    assert merged.document.assets == (asset,)


def test_pruning_drops_a_picture_once_the_selected_instructions_leave_it() -> None:
    asset = _asset("d")
    head = _document(
        items=(_free_text("item_001", 1, "Fråga ett"),),
        instructions=_stem(asset.asset_id),
        assets=(asset,),
    )
    # The head instructions are still the delivered revision, so the new proposal wins.
    progress = ConversionProgress(instructions_digest=_instructions_digest(head.instructions))

    merged = merge_conversion(
        head=head,
        progress=progress,
        target=ConversionTarget(units=(), instructions=_NEW_INSTRUCTION),
    )

    assert merged.document.instructions == _NEW_INSTRUCTION
    assert merged.document.assets == ()


def test_a_delivered_picture_is_kept_when_the_selected_parent_references_it() -> None:
    asset = _asset("e")
    head = _document(items=(_free_text("item_001", 1, "Källtext"),))
    target = ConversionTarget(
        units=(
            CandidateUnit(
                unit_id="q1",
                question=True,
                state=ConversionUnitState.READY,
                items=(_free_text("item_500", 1, "Fråga ett"),),
            ),
        ),
        parents=(
            NativeExamParent(
                parent_id="parent_001",
                place=0,
                instruction=_stem(asset.asset_id),
                item_ids=("item_500",),
            ),
        ),
        assets=(asset,),
    )
    # No parents were delivered before, so the head parents still match the digest and
    # the target's parent becomes the selected one.
    progress = ConversionProgress(parents_digest=digest_json([]))

    merged = merge_conversion(head=head, progress=progress, target=target)

    (parent,) = merged.document.parents
    (item,) = (item for item in merged.document.items if item.item_id in parent.item_ids)
    assert parent.item_ids == (item.item_id,)
    assert body_asset_ids(parent.instruction) == (asset.asset_id,)
    assert merged.document.assets == (asset,)
