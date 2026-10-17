"""Adapt native leaf interactions, their prompts and resources to QTI items.

Document and parent assembly belongs to ``examnet_qti_export``; this module
owns the single authoritative projection for each native leaf kind.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiImageResource,
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiPromptParagraph,
    ExamNetQtiTextEntryGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import ExamLanguageLabels
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_prompt import (
    body_carries_formatting,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_prompt import (
    prompt_paragraphs as body_prompt_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamAsset
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.errors import DomainError, ErrorCode

_INTERACTION_TYPE_BY_KIND = {
    NativeExamItemKind.FREE_TEXT: ExamNetQtiInteractionType.FREE_TEXT,
    NativeExamItemKind.SINGLE_CHOICE: ExamNetQtiInteractionType.SINGLE_CHOICE,
    NativeExamItemKind.MULTIPLE_RESPONSE: ExamNetQtiInteractionType.MULTIPLE_RESPONSE,
    NativeExamItemKind.GAP_FILL: ExamNetQtiInteractionType.GAP_FILL,
    NativeExamItemKind.INLINE_CHOICE: ExamNetQtiInteractionType.INLINE_CHOICE,
    NativeExamItemKind.MATCHING: ExamNetQtiInteractionType.MATCHING,
    NativeExamItemKind.ORDERING: ExamNetQtiInteractionType.ORDERING,
}


def leaf_qti_item(
    *,
    item: NativeExamItem,
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
    labels: ExamLanguageLabels,
    first_image_number: int = 1,
) -> ExamNetQtiItem:
    base_item = ExamNetQtiItem(
        item_id=safe_identifier(item.item_id),
        sequence=item.sequence,
        title=labels.item_title(item),
        interaction_type=_INTERACTION_TYPE_BY_KIND[item.kind],
        prompt_lines=item.plain_text_lines(),
        prompt_paragraphs=_prompt_paragraphs(item),
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
    if item.kind is NativeExamItemKind.FREE_TEXT:
        return _free_text_item(item, base_item)
    if item.kind in (
        NativeExamItemKind.SINGLE_CHOICE,
        NativeExamItemKind.MULTIPLE_RESPONSE,
    ):
        return _choice_item(item, base_item)
    if item.kind is NativeExamItemKind.MATCHING:
        return _matching_item(item, base_item)
    if item.kind is NativeExamItemKind.ORDERING:
        return _ordering_item(item, base_item)
    if item.kind is NativeExamItemKind.INLINE_CHOICE:
        return _inline_choice_item(item, base_item)
    return _gap_fill_item(item, base_item, labels)


def _free_text_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    if item.points is None or item.points <= 0:
        return replace(base_item, evaluation_mode=ExamNetQtiEvaluationMode.MANUAL_UNKEYED)
    # Criteria become one 1-point rule row per criterion point (Q13).
    # Criterion text is never written to the package.
    criterion_points = 1 if item.criteria else item.points
    return replace(base_item, free_text_criterion_points=criterion_points)


def _choice_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    # native_export_blockers already blocks keyed items without an answer key.
    correct_ids: tuple[str, ...] = ()
    if item.answer_key.origin is not NativeAnswerKeyOrigin.ABSENT:
        correct_ids = tuple(
            safe_identifier(choice_id) for choice_id in item.answer_key.correct_choice_ids
        )
    choices: list[ExamNetQtiChoice] = []
    for choice in item.choices:
        label = _plain_label(choice.body)
        if not label:
            continue
        choices.append(
            ExamNetQtiChoice(
                identifier=safe_identifier(choice.choice_id),
                text=label,
                body=body_prompt_paragraphs(choice.body),
            )
        )
    return replace(
        base_item,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        choices=tuple(choices),
        correct_choice_identifiers=correct_ids,
    )


def _ordering_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    # Steps are item.choices in key order; the student sees them in the saved print
    # order, so the visible list never shows the answer. The correct response is the key.
    by_id = {choice.choice_id: choice for choice in item.choices}
    shown = [by_id[choice_id] for choice_id in item.print_order]
    return replace(
        base_item,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        choices=tuple(
            ExamNetQtiChoice(
                identifier=safe_identifier(choice.choice_id),
                text=_plain_label(choice.body),
                body=body_prompt_paragraphs(choice.body),
            )
            for choice in shown
        ),
        correct_choice_identifiers=tuple(
            safe_identifier(choice.choice_id) for choice in item.choices
        ),
    )


def _matching_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    # Both lists retain every entry in native order, including distractors.
    left = {entry.left_id: _plain_label(entry.body) for entry in item.match_left}
    right = {entry.right_id: _plain_label(entry.body) for entry in item.match_right}
    pairs: tuple[ExamNetQtiMatchPair, ...] = ()
    if item.answer_key.origin is not NativeAnswerKeyOrigin.ABSENT:
        pairs = tuple(
            ExamNetQtiMatchPair(
                left_identifier=safe_identifier(pair.left_id),
                left_text=" ".join(left[pair.left_id].split()),
                right_identifier=safe_identifier(pair.right_id),
                right_text=" ".join(right[pair.right_id].split()),
            )
            for pair in item.answer_key.match_pairs
        )
    return replace(
        base_item,
        evaluation_mode=ExamNetQtiEvaluationMode.AUTOMATIC,
        match_pairs=pairs,
        match_left=tuple(
            ExamNetQtiMatchEntry(
                safe_identifier(entry.left_id),
                _plain_label(entry.body),
                body_prompt_paragraphs(entry.body),
            )
            for entry in item.match_left
        ),
        match_right=tuple(
            ExamNetQtiMatchEntry(
                safe_identifier(entry.right_id),
                _plain_label(entry.body),
                body_prompt_paragraphs(entry.body),
            )
            for entry in item.match_right
        ),
    )


def _gap_fill_item(
    item: NativeExamItem, base_item: ExamNetQtiItem, labels: ExamLanguageLabels
) -> ExamNetQtiItem:
    accepted_values_by_gap_id = {
        gap.gap_id: tuple(
            value.strip()
            for value in (*gap.accepted_values, *gap.automatic_values)
            if value.strip()
        )
        for gap in item.gaps
    }
    return replace(
        base_item,
        text_entry_gaps=tuple(
            ExamNetQtiTextEntryGap(
                response_identifier=f"RESPONSE_{safe_identifier(gap_id)}",
                label=labels.gap_label(index),
                accepted_values=accepted_values_by_gap_id.get(gap_id, ()),
            )
            for index, gap_id in enumerate(placed_gap_ids(item), start=1)
        ),
    )


def _inline_choice_item(item: NativeExamItem, base_item: ExamNetQtiItem) -> ExamNetQtiItem:
    gaps = {gap.gap_id: gap for gap in item.gaps}
    return replace(
        base_item,
        inline_choice_gaps=tuple(
            ExamNetQtiInlineChoiceGap(
                response_identifier=f"RESPONSE_{safe_identifier(gap_id)}",
                options=tuple(
                    ExamNetQtiChoice(
                        identifier=safe_identifier(option.choice_id),
                        text=_plain_label(option.body),
                        body=body_prompt_paragraphs(option.body),
                    )
                    for option in gaps[gap_id].options
                ),
                correct_option_identifier=safe_identifier(
                    next(
                        option.choice_id
                        for option in gaps[gap_id].options
                        if option.choice_id == gaps[gap_id].correct_option_id
                    )
                ),
            )
            for gap_id in placed_gap_ids(item)
        ),
    )


def placed_gap_ids(item: NativeExamItem) -> tuple[str, ...]:
    """Return gap ids in body placement order for prompt/response binding."""
    return tuple(
        segment.gap_id
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeGapSegment)
    )


def _prompt_paragraphs(item: NativeExamItem) -> tuple[ExamNetQtiPromptParagraph, ...]:
    """Keep positioned picture/gap carriers and every formatting carrier."""
    if (
        item.kind not in (NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE)
        and not item.body_asset_ids()
        and not body_carries_formatting(item.body)
    ):
        return ()
    return body_prompt_paragraphs(item.body, gap_ids=placed_gap_ids(item))


def _plain_label(body: tuple[NativeParagraph, ...]) -> str:
    """The whitespace-normalized plain text every non-rendering QTI reader sees."""
    return " ".join(body_plain_text(body).split())


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


def safe_identifier(value: str) -> str:
    return value.replace("-", "_")
