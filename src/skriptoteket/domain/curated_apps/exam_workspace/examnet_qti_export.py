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
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    ExamLanguageLabels,
    exam_language_labels,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeExamParent,
    NativeGapSegment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode

NO_EXPORT_ASSETS: Mapping[str, bytes] = MappingProxyType({})

_INTERACTION_TYPE_BY_KIND = {
    NativeExamItemKind.FREE_TEXT: ExamNetQtiInteractionType.FREE_TEXT,
    NativeExamItemKind.SINGLE_CHOICE: ExamNetQtiInteractionType.SINGLE_CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE: ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    NativeExamItemKind.GAP_FILL: ExamNetQtiInteractionType.GAP_FILL,
    NativeExamItemKind.MATCHING: ExamNetQtiInteractionType.MATCHING,
}


def native_exam_to_examnet_qti_items(
    document: NativeExamDocument,
    *,
    assets_by_id: Mapping[str, bytes] = NO_EXPORT_ASSETS,
) -> tuple[ExamNetQtiItem, ...]:
    """Convert the native exam to reusable Exam.net QTI items.

    A standalone native item becomes one QTI item. The children of a native parent
    become one parent QTI item, placed where the parent's first child stands.
    """

    assets = {asset.asset_id: asset for asset in document.assets}
    labels = exam_language_labels(document)
    qti_items: list[ExamNetQtiItem] = []
    emitted_parent_ids: set[str] = set()
    for item in document.items:
        parent = document.parent_of(item.item_id)
        if parent is None:
            qti_items.append(
                _qti_item(item=item, assets=assets, assets_by_id=assets_by_id, labels=labels)
            )
        elif parent.parent_id not in emitted_parent_ids:
            emitted_parent_ids.add(parent.parent_id)
            children = tuple(document.item_by_id(item_id) for item_id in parent.item_ids)
            qti_items.append(
                _parent_qti_item(
                    parent=parent,
                    children=children,
                    assets=assets,
                    assets_by_id=assets_by_id,
                    labels=labels,
                )
            )
    return tuple(qti_items)


def _parent_qti_item(
    *,
    parent: NativeExamParent,
    children: tuple[NativeExamItem, ...],
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
    labels: ExamLanguageLabels,
) -> ExamNetQtiItem:
    qti_children: list[ExamNetQtiItem] = []
    image_count = 0
    for child in children:
        qti_child = _qti_item(
            item=child,
            assets=assets,
            assets_by_id=assets_by_id,
            labels=labels,
            first_image_number=image_count + 1,
        )
        image_count += len(qti_child.image_resources)
        qti_children.append(qti_child)
    first = qti_children[0]
    parent_id = _safe_identifier(parent.parent_id)
    if len(qti_children) == 1 and first.interaction_type is not ExamNetQtiInteractionType.GAP_FILL:
        # One child has nothing to share: a stem outside its interaction would be
        # rejected, so the instruction joins the child's own prompt.
        return replace(
            first, item_id=parent_id, prompt_lines=(*parent.instruction, *first.prompt_lines)
        )
    manual = any(
        child.evaluation_mode is ExamNetQtiEvaluationMode.MANUAL_UNKEYED for child in qti_children
    )
    scored = [child.max_score for child in qti_children if child.max_score is not None]
    return ExamNetQtiItem(
        item_id=parent_id,
        sequence=first.sequence,
        title=_parent_title(children, labels),
        interaction_type=first.interaction_type,
        prompt_lines=parent.instruction,
        max_score=sum(scored) if scored else None,
        evaluation_mode=(
            ExamNetQtiEvaluationMode.MANUAL_UNKEYED
            if manual
            else ExamNetQtiEvaluationMode.AUTOMATIC
        ),
        image_resources=tuple(image for child in qti_children for image in child.image_resources),
        instruction_lines=parent.instruction,
        children=tuple(qti_children),
    )


def _qti_item(
    *,
    item: NativeExamItem,
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
    labels: ExamLanguageLabels,
    first_image_number: int = 1,
) -> ExamNetQtiItem:
    base_item = _base_qti_item(
        item=item,
        assets=assets,
        assets_by_id=assets_by_id,
        labels=labels,
        first_image_number=first_image_number,
    )
    if item.kind is NativeExamItemKind.FREE_TEXT:
        return _free_text_item(item, base_item)
    if item.kind in (
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.MULTIPLE_RESPONSE,
    ):
        return _choice_item(item, base_item)
    if item.kind is NativeExamItemKind.MATCHING:
        return _matching_item(item, base_item)
    return _gap_fill_item(item, base_item, labels)


def _base_qti_item(
    *,
    item: NativeExamItem,
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
    labels: ExamLanguageLabels,
    first_image_number: int,
) -> ExamNetQtiItem:
    return ExamNetQtiItem(
        item_id=_safe_identifier(item.item_id),
        sequence=item.sequence,
        title=labels.item_title(item),
        interaction_type=_INTERACTION_TYPE_BY_KIND[item.kind],
        prompt_lines=item.plain_text_lines(),
        max_score=item.points,
        source_item_type=item.kind.value,
        image_resources=_image_resources(
            item=item,
            assets=assets,
            assets_by_id=assets_by_id,
            labels=labels,
            first_image_number=first_image_number,
        ),
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


def _matching_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    # As for choice items, `native_export_blockers` already blocks an unkeyed matching item.
    # Both visible lists keep the native order and every entry, an unpaired right entry
    # (a distractor) included; the pairs only feed the response and scoring data.
    left = {entry.left_id: entry.text for entry in item.match_left}
    right = {entry.right_id: entry.text for entry in item.match_right}
    pairs: tuple[ExamNetQtiMatchPair, ...] = ()
    if item.answer_key.origin is not NativeAnswerKeyOrigin.ABSENT:
        pairs = tuple(
            ExamNetQtiMatchPair(
                left_identifier=_safe_identifier(pair.left_id),
                left_text=" ".join(left[pair.left_id].split()),
                right_identifier=_safe_identifier(pair.right_id),
                right_text=" ".join(right[pair.right_id].split()),
            )
            for pair in item.answer_key.match_pairs
        )
    return replace(
        base_item,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        match_pairs=pairs,
        match_left=tuple(
            ExamNetQtiMatchEntry(_safe_identifier(entry.left_id), " ".join(entry.text.split()))
            for entry in item.match_left
        ),
        match_right=tuple(
            ExamNetQtiMatchEntry(_safe_identifier(entry.right_id), " ".join(entry.text.split()))
            for entry in item.match_right
        ),
    )


def _gap_fill_item(
    item: NativeExamItem, base_item: ExamNetQtiItem, labels: ExamLanguageLabels
) -> ExamNetQtiItem:
    accepted_values_by_gap_id = {
        gap.gap_id: tuple(value.strip() for value in gap.accepted_values if value.strip())
        for gap in item.gaps
    }
    return replace(
        base_item,
        text_entry_gaps=tuple(
            ExamNetQtiTextEntryGap(
                response_identifier=f"RESPONSE_{_safe_identifier(gap_id)}",
                label=labels.gap_label(index),
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
    labels: ExamLanguageLabels,
    first_image_number: int,
) -> tuple[ExamNetQtiImageResource, ...]:
    resources: list[ExamNetQtiImageResource] = []
    for index, asset_id in enumerate(item.body_asset_ids(), start=1):
        number = first_image_number + index - 1
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
                asset_id=f"image_{number:03d}",
                filename=f"{item.item_id}-image-{number:03d}.png",
                media_type=asset.media_type,
                payload=payload,
                alt_text=labels.image_alt(index),
                source_reference=asset_id,
            )
        )
    return tuple(resources)


def _parent_title(children: tuple[NativeExamItem, ...], labels: ExamLanguageLabels) -> str:
    """The span of the children's printed labels (D20); running numbers when one lacks it."""
    printed = [child.printed_label for child in children if child.printed_label]
    if len(printed) == len(children):
        return labels.printed_span(printed[0], printed[-1])
    return labels.question_label(children[0].sequence, children[-1].sequence)


def _safe_identifier(value: str) -> str:
    return value.replace("-", "_")
