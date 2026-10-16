"""Assemble native asset metadata and payloads from referenced DOCX pictures."""

import hashlib
from collections.abc import Iterable, Mapping
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk, DocxImage
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamAsset
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_asset_ids


def asset_manifest(
    items: Iterable[NativeExamItem],
    chunks: Iterable[DocxChunk],
    *,
    shared_bodies: Iterable[tuple[NativeParagraph, ...]] = (),
) -> tuple[tuple[NativeExamAsset, ...], Mapping[str, bytes]]:
    """The pictures the document references: native metadata and payloads, in asset-id order.

    Every picture an item's student body references, every picture a shared instruction
    body places at its source position (a parent or the document-global instruction), and
    every picture an item's stored retry source keeps (facit and read-only context
    included) is carried, because the native contract rejects an orphan asset; the QTI
    export reads the body references only, so a source-only picture never reaches a
    student. The container requires payloads to match the document's asset list exactly.
    """
    images: dict[str, DocxImage] = {}
    for chunk in chunks:
        for image in chunk.images:
            images.setdefault(image.asset_id, image)
    referenced = sorted(
        {
            asset_id
            for item in items
            for asset_id in (*item.body_asset_ids(), *item.source_asset_ids())
        }
        | {asset_id for body in shared_bodies for asset_id in body_asset_ids(body)}
    )
    missing = [asset_id for asset_id in referenced if asset_id not in images]
    if missing:
        raise ValueError(f"items reference unknown source pictures: {', '.join(missing)}")
    assets = tuple(
        NativeExamAsset(
            asset_id=asset_id,
            sha256=hashlib.sha256(images[asset_id].payload).hexdigest(),
            media_type=images[asset_id].media_type,
            byte_length=len(images[asset_id].payload),
            width=images[asset_id].width,
            height=images[asset_id].height,
        )
        for asset_id in referenced
    )
    payloads = {asset_id: images[asset_id].payload for asset_id in referenced}
    return assets, MappingProxyType(payloads)
