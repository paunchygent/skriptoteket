"""Map read QTI items back to the native exam the workspace exports.

Purpose:
    Invert ``examnet_qti_export`` and ``examnet_qti_leaf_items``: every read
    ``ExamNetQtiItem`` becomes the native item, points and answer key the export
    started from, unsupported package items become the same visible notes the
    DigiExam import writes, and one ``ExamWorkspaceContainerContent`` holds
    revision one plus exactly the referenced picture payloads (Q1-Q3).

Relationships:
    - Consumed by the QTI import application handler after the package readers
      produce ``ExamNetQtiReadItem`` values in package order.
    - Mirrors ``digiexam_import``: notes, asset ids, review and import record.
    - Reads and writes only the native document models, so it stays pure.
    - ``qti_import_leaf_items`` maps one leaf item to its native item, points
      and answer key; ``qti_import_body`` assembles shared native prompt bodies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import PurePath
from uuid import UUID

from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_import_contracts import (
    ExamNetQtiReadItem,
    ExamNetQtiUnsupportedItem,
    ExamNetQtiUnsupportedReason,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamHeader,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import_body import paragraphs
from skriptoteket.domain.curated_apps.exam_workspace.qti_import_leaf_items import (
    KINDS,
    leaf_item,
    native_media_type,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_asset_ids
from skriptoteket.domain.errors import validation_error

_UNSUPPORTED_NOTES = {
    ExamNetQtiUnsupportedReason.INTERACTION: ("frågetypen stöds inte och importerades inte."),
    ExamNetQtiUnsupportedReason.IMAGE: (
        "en bild i frågan kunde inte läsas och frågan importerades inte."
    ),
}


@dataclass
class _AssetRegistry:
    """Collect picture payloads once per deterministic asset id."""

    assets: dict[str, NativeExamAsset] = field(default_factory=dict)
    payloads: dict[str, bytes] = field(default_factory=dict)

    def register(self, resource: ExamNetQtiImageResource) -> str:
        digest = sha256(resource.payload).hexdigest()
        asset_id = f"asset_{digest[:16]}"
        self.assets.setdefault(
            asset_id,
            NativeExamAsset(
                asset_id=asset_id,
                sha256=digest,
                media_type=native_media_type(resource.media_type),
                byte_length=len(resource.payload),
                width=None,
                height=None,
            ),
        )
        self.payloads.setdefault(asset_id, resource.payload)
        return asset_id


def build_native_exam_from_qti(
    *,
    items: tuple[ExamNetQtiReadItem, ...],
    document_id: UUID,
    source_filename: str,
    source_sha256: str,
    course: ExamCourseChoice | None = None,
) -> ExamWorkspaceContainerContent:
    """Return revision one, its referenced payloads and the skipped-item notes."""

    native_items: list[NativeExamItem] = []
    parents: list[NativeExamParent] = []
    notes: list[str] = []
    assets = _AssetRegistry()
    for source in items:
        if isinstance(source, ExamNetQtiUnsupportedItem):
            notes.append(_unsupported_note(source))
            continue
        if source.interaction_type is ExamNetQtiInteractionType.INFORMATION:
            _append_information_parent(
                source,
                native_items=native_items,
                parents=parents,
                assets=assets,
            )
            continue
        if source.children:
            _append_parent(
                source,
                native_items=native_items,
                parents=parents,
                notes=notes,
                assets=assets,
            )
            continue
        leaf = leaf_item(source, sequence=len(native_items) + 1, assets=assets)
        if leaf is None:
            notes.append(_interaction_note(source.sequence, _opening_text(source)))
            continue
        native_items.append(leaf)
    if not native_items:
        raise validation_error("QTI-paketet innehåller inga frågetyper som stöds.")
    referenced = {asset_id for item in native_items for asset_id in item.body_asset_ids()}
    referenced.update(
        asset_id for parent in parents for asset_id in body_asset_ids(parent.instruction)
    )
    try:
        document = NativeExamDocument(
            document_id=document_id,
            revision=1,
            title=PurePath(source_filename).stem,
            header=NativeExamHeader(course=course),
            items=tuple(native_items),
            parents=tuple(parents),
            assets=tuple(
                asset for asset_id, asset in assets.assets.items() if asset_id in referenced
            ),
            origin=NativeExamDocumentOrigin(
                kind="qti_import",
                source_filename=source_filename,
                source_sha256=source_sha256,
            ),
        )
    except ValidationError as exc:
        raise validation_error("QTI-paketet kunde inte läsas som ett prov.") from exc
    return ExamWorkspaceContainerContent(
        document=document,
        assets_by_id={
            asset_id: payload
            for asset_id, payload in assets.payloads.items()
            if asset_id in referenced
        },
        notes=tuple(notes),
    )


def _append_information_parent(
    source: ExamNetQtiItem,
    *,
    native_items: list[NativeExamItem],
    parents: list[NativeExamParent],
    assets: _AssetRegistry,
) -> None:
    """Map an information block to a childless part at the current item count."""

    image_ids = tuple(assets.register(resource) for resource in source.image_resources)
    instruction = paragraphs(
        source.prompt_paragraphs,
        image_ids=image_ids,
        plain_lines=source.instruction_lines,
    )
    parents.append(
        NativeExamParent(
            parent_id=f"parent_{len(parents) + 1:03d}",
            place=len(native_items),
            instruction=instruction,
            item_ids=(),
        )
    )


def _append_parent(
    source: ExamNetQtiItem,
    *,
    native_items: list[NativeExamItem],
    parents: list[NativeExamParent],
    notes: list[str],
    assets: _AssetRegistry,
) -> None:
    """Map a stem and every child, keeping the children consecutive in item order."""

    place = len(native_items)
    child_ids: list[str] = []
    for child in source.children:
        if KINDS[child.interaction_type] is NativeExamItemKind.ORDERING:
            # Ordering questions are standalone only; a parent cannot hold one.
            notes.append(_interaction_note(child.sequence, _opening_text(child)))
            continue
        leaf = leaf_item(child, sequence=len(native_items) + 1, assets=assets)
        if leaf is None:
            notes.append(_interaction_note(child.sequence, _opening_text(child)))
            continue
        native_items.append(leaf)
        child_ids.append(leaf.item_id)
    if not child_ids:
        return
    stem_images = len(source.image_resources) - sum(
        len(child.image_resources) for child in source.children
    )
    stem_image_ids = tuple(
        assets.register(resource) for resource in source.image_resources[:stem_images]
    )
    instruction = paragraphs(
        source.prompt_paragraphs,
        image_ids=stem_image_ids,
        plain_lines=source.instruction_lines,
    )
    parents.append(
        NativeExamParent(
            parent_id=f"parent_{len(parents) + 1:03d}",
            place=place,
            instruction=instruction,
            item_ids=tuple(child_ids),
        )
    )


def _unsupported_note(source: ExamNetQtiUnsupportedItem) -> str:
    return _note(source.sequence, source.opening_text[:100], source.reason)


def _interaction_note(sequence: int, opening_text: str) -> str:
    return _note(sequence, opening_text[:100], ExamNetQtiUnsupportedReason.INTERACTION)


def _note(sequence: int, opening: str, reason: ExamNetQtiUnsupportedReason) -> str:
    prefix = f"Fråga {sequence}" + (f" – {opening}" if opening else "")
    return f"{prefix}: {_UNSUPPORTED_NOTES[reason]}"


def _opening_text(item: ExamNetQtiItem) -> str:
    rendered = " ".join(" ".join(item.prompt_lines).split())
    if rendered:
        return rendered
    return " ".join(
        segment.text
        for paragraph in item.prompt_paragraphs
        for segment in paragraph.segments
        if isinstance(segment, ExamNetQtiPromptText)
    )
