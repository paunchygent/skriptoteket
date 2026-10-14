"""Asset reconciliation for a progressive DOCX conversion merge (TASK-SKRIPT-39-05-09 D2).

A merged document keeps the saved head's pictures plus the conversion's delivered pictures,
minus any picture no merged item still references. Asset ids are content-addressed, so a
picture delivered twice is one asset. Payload selection and the Actor-owned vault persistence
stay with the conversion progress port; this module only decides which assets the merged
document keeps.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamItem,
)


def merged_assets(
    *,
    head: NativeExamDocument,
    delivered: tuple[NativeExamAsset, ...] | None,
    items: tuple[NativeExamItem, ...],
) -> tuple[NativeExamAsset, ...]:
    """The head's and the conversion's pictures, minus any the merged items no longer use.

    Asset ids are content-addressed, so a picture delivered twice is one asset. Every
    picture an item's student body or its stored retry source references is kept; the native
    contract rejects an orphan asset, so a picture whose item the teacher removed is dropped.
    """
    by_id = {asset.asset_id: asset for asset in head.assets}
    for asset in delivered or ():
        by_id.setdefault(asset.asset_id, asset)
    referenced = {
        asset_id
        for item in items
        for asset_id in (*item.body_asset_ids(), *item.source_asset_ids())
    }
    return tuple(by_id[asset_id] for asset_id in sorted(by_id) if asset_id in referenced)
