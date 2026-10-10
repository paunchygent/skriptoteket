"""Native exam adapter for Exam.net QTI package generation.

Purpose:
    Convert native exam workspace documents into the source-neutral Exam.net
    QTI item contract without changing planner, XML, or writer semantics.

Relationships:
    - Consumes `domain.curated_apps.exam_workspace.native_exam_document`.
    - Emits `domain.curated_apps.exam_conversion.examnet_qti_contracts` items
      for the reusable QTI package planner.
    - Mirrors the construction conventions of
      `domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeGapSegment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

NO_EXPORT_ASSETS: Mapping[str, bytes] = MappingProxyType({})

_INTERACTION_TYPE_BY_KIND = {
    NativeExamItemKind.FREE_TEXT: ExamNetQtiInteractionType.FREE_TEXT,
    NativeExamItemKind.SINGLE_CHOICE: ExamNetQtiInteractionType.SINGLE_CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE: ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    NativeExamItemKind.GAP_FILL: ExamNetQtiInteractionType.GAP_FILL,
}


def native_exam_to_examnet_qti_items(
    document: NativeExamDocument,
    *,
    assets_by_id: Mapping[str, bytes] = NO_EXPORT_ASSETS,
) -> tuple[ExamNetQtiItem, ...]:
    """Convert every native exam item to a reusable Exam.net QTI item."""

    assets = {asset.asset_id: asset for asset in document.assets}
    return tuple(
        _qti_item(item=item, assets=assets, assets_by_id=assets_by_id) for item in document.items
    )


def _qti_item(
    *,
    item: NativeExamItem,
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
) -> ExamNetQtiItem:
    base_item = _base_qti_item(item=item, assets=assets, assets_by_id=assets_by_id)
    if item.kind is NativeExamItemKind.FREE_TEXT:
        return _free_text_item(item, base_item)
    if item.kind in (
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.MULTIPLE_RESPONSE,
    ):
        return _choice_item(item, base_item)
    return _gap_fill_item(item, base_item)


def _base_qti_item(
    *,
    item: NativeExamItem,
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id=_safe_identifier(item.item_id),
        sequence=item.sequence,
        title=_item_title(item),
        interaction_type=_INTERACTION_TYPE_BY_KIND[item.kind],
        prompt_lines=item.plain_text_lines(),
        max_score=item.points,
        source_item_type=item.kind.value,
        image_resources=_image_resources(item=item, assets=assets, assets_by_id=assets_by_id),
    )


def _free_text_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    if item.points is None or item.points <= 0:
        return replace(base_item, evaluation_mode=ExamNetQtiEvaluationMode.MANUAL_UNKEYED)
    return replace(base_item, free_text_criterion_points=item.points)


def _choice_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    # Defensive second guard: `native_export_blockers` (reason `missing_answer_key`)
    # already blocks keyed items without a key before export. An unkeyed keyed
    # item must never be exported; Exam.net would drop or mis-handle it.
    correct_ids: tuple[str, ...] = ()
    if item.answer_key.origin is not NativeAnswerKeyOrigin.ABSENT:
        correct_ids = tuple(
            _safe_identifier(choice_id) for choice_id in item.answer_key.correct_choice_ids
        )
    return replace(
        base_item,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        choices=tuple(
            ExamNetQtiChoice(
                identifier=_safe_identifier(choice.choice_id),
                text=" ".join(choice.text.split()),
            )
            for choice in item.choices
            if choice.text.strip()
        ),
        correct_choice_identifiers=correct_ids,
    )


def _gap_fill_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    accepted_values_by_gap_id = {
        gap.gap_id: tuple(value.strip() for value in gap.accepted_values if value.strip())
        for gap in item.gaps
    }
    return replace(
        base_item,
        text_entry_gaps=tuple(
            ExamNetQtiTextEntryGap(
                response_identifier=f"RESPONSE_{_safe_identifier(gap_id)}",
                label=f"Lucka {index}",
                accepted_values=accepted_values_by_gap_id.get(gap_id, ()),
            )
            for index, gap_id in enumerate(_placed_gap_ids(item), start=1)
        ),
    )


def _placed_gap_ids(item: NativeExamItem) -> tuple[str, ...]:
    """Return gap ids in body placement order: the planner binds the ``[___]``
    markers rendered by ``plain_text_lines`` to text-entry gaps in order."""

    return tuple(
        segment.gap_id
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeGapSegment)
    )


def _image_resources(
    *,
    item: NativeExamItem,
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
) -> tuple[ExamNetQtiImageResource, ...]:
    resources: list[ExamNetQtiImageResource] = []
    for index, asset_id in enumerate(item.body_asset_ids(), start=1):
        payload = assets_by_id.get(asset_id)
        if payload is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Exam item references an asset without payload bytes.",
                details={"item_id": item.item_id, "asset_id": asset_id},
            )
        asset = assets[asset_id]
        resources.append(
            ExamNetQtiImageResource(
                asset_id=f"image_{index:03d}",
                filename=f"{item.item_id}-image-{index:03d}.png",
                media_type=asset.media_type,
                payload=payload,
                alt_text=f"Bild {index} till {_item_title(item)}",
                source_reference=asset_id,
            )
        )
    return tuple(resources)


def _item_title(item: NativeExamItem) -> str:
    return item.title or f"Fråga {item.sequence}"


def _safe_identifier(value: str) -> str:
    return value.replace("-", "_")
