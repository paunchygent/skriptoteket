"""Asset reconciliation for a progressive DOCX conversion merge (TASK-SKRIPT-39-05-09 D2).

A merged document keeps the saved head's pictures plus the conversion's delivered pictures,
minus any picture no merged body still references. A body is an item's student text or
stored retry source, or a shared instruction — the document's global instructions or a
parent's instruction. Asset ids are content-addressed, so a picture delivered twice is one
asset. Payload selection and the Actor-owned vault persistence stay with the conversion
progress port; this module only decides which assets the merged document keeps.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamItem,
    NativeExamParent,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_asset_ids


def merged_assets(
    *,
    head: NativeExamDocument,
    delivered: tuple[NativeExamAsset, ...] | None,
    items: tuple[NativeExamItem, ...],
    instructions: tuple[NativeParagraph, ...],
    parents: tuple[NativeExamParent, ...],
) -> tuple[NativeExamAsset, ...]:
    """The head's and the conversion's pictures, minus any the merged document no longer uses.

    Asset ids are content-addressed, so a picture delivered twice is one asset. Every picture
    a merged item's student body, its stored retry source, or a merged shared instruction (the
    selected global instructions or a selected parent's instruction) references is kept; the
    native contract rejects an orphan asset, so a picture whose last carrier the teacher
    removed is dropped.
    """
    by_id = {asset.asset_id: asset for asset in head.assets}
    for asset in delivered or ():
        by_id.setdefault(asset.asset_id, asset)
    referenced = {
        asset_id
        for item in items
        for asset_id in (*item.body_asset_ids(), *item.source_asset_ids())
    }
    for body in (instructions, *(parent.instruction for parent in parents)):
        referenced.update(body_asset_ids(body))
    return tuple(by_id[asset_id] for asset_id in sorted(by_id) if asset_id in referenced)
