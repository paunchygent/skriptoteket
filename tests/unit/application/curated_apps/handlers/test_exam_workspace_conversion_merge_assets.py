"""Pictures survive progressive merges and drop when no item references them (D2)."""

from hashlib import sha256
from typing import Literal

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    first_conversion,
    merge_conversion,
    target_from_update,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAssetSegment,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetrySource,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    DOCUMENT_ID,
    choice,
)

_BODY = "Fråga ett"


def _asset(
    asset_id: str,
    payload: bytes,
    media_type: Literal["image/png", "image/jpeg"] = "image/png",
) -> NativeExamAsset:
    return NativeExamAsset(
        asset_id=asset_id,
        sha256=sha256(payload).hexdigest(),
        media_type=media_type,
        byte_length=len(payload),
    )


def _item(
    *, body_asset_ids: tuple[str, ...] = (), retry_asset_ids: tuple[str, ...] = ()
) -> NativeExamItem:
    segments: list[NativeSegment] = [NativeTextSegment(text=_BODY)]
    segments.extend(NativeAssetSegment(asset_id=asset_id) for asset_id in body_asset_ids)
    item = choice("p1", _BODY).model_copy(
        update={"body": (NativeParagraph(segments=tuple(segments)),)}
    )
    if not retry_asset_ids:
        return item
    return item.model_copy(
        update={
            "retry_source": NativeExamRetrySource(
                chunks=(
                    NativeExamRetryChunk(
                        anchor="p1",
                        kind="paragraph",
                        text=_BODY,
                        marked_text=_BODY,
                        images=tuple(
                            NativeExamRetryImage(asset_id=asset_id, offset=0, marked_offset=0)
                            for asset_id in retry_asset_ids
                        ),
                    ),
                ),
                label_kind=NativeExamItemKind.FREE_TEXT,
            )
        }
    )


def _update(item: NativeExamItem, assets: tuple[NativeExamAsset, ...]) -> ConversionUpdate:
    document = NativeExamDocument(
        document_id=DOCUMENT_ID,
        revision=1,
        title="Prov",
        items=(item,),
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    return ConversionUpdate(
        filled=("q1",),
        pending=(),
        document=document,
        item_ids={"q1": (item.item_id,)},
        extra_item_ids=(),
        parent_ids={},
    )


def test_merge_keeps_a_new_picture_and_drops_the_orphan_it_replaced() -> None:
    asset_a = _asset("asset_" + "a" * 16, b"one")
    asset_b = _asset("asset_" + "b" * 16, b"two")
    head = first_conversion(
        update=_update(_item(body_asset_ids=(asset_a.asset_id,)), (asset_a,)),
        progress=ConversionProgress.from_question_ids(["q1"]),
    )
    second = _update(_item(body_asset_ids=(asset_b.asset_id,)), (asset_b,))

    merged = merge_conversion(
        head=head.document, progress=head.progress, target=target_from_update(second)
    )

    assert [asset.asset_id for asset in merged.document.assets] == [asset_b.asset_id]


def test_merge_keeps_a_picture_only_the_stored_retry_source_references() -> None:
    body_asset = _asset("asset_" + "c" * 16, b"body")
    retry_asset = _asset("asset_" + "d" * 16, b"facit", media_type="image/jpeg")
    head = first_conversion(
        update=_update(_item(body_asset_ids=(body_asset.asset_id,)), (body_asset,)),
        progress=ConversionProgress.from_question_ids(["q1"]),
    )
    second = _update(
        _item(body_asset_ids=(body_asset.asset_id,), retry_asset_ids=(retry_asset.asset_id,)),
        (body_asset, retry_asset),
    )

    merged = merge_conversion(
        head=head.document, progress=head.progress, target=target_from_update(second)
    )

    assert {asset.asset_id for asset in merged.document.assets} == {
        body_asset.asset_id,
        retry_asset.asset_id,
    }
