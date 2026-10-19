"""Assemble native documents and parents into source-neutral Exam.net QTI items.

Leaf interaction, prompt and resource adaptation belongs to
``examnet_qti_leaf_items``. This module owns document order, shared stems and
parent grouping without changing planner, XML or writer semantics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    SWEDISH_EXAM_LABELS,
    ExamExportLabels,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_leaf_items import (
    leaf_qti_item,
    placed_gap_ids,
    safe_identifier,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_prompt import (
    image_resources as stem_image_resources,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_prompt import (
    prompt_paragraphs as body_prompt_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    is_empty_body,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_outline import (
    OutlineQuestion,
    document_outline,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines

NO_EXPORT_ASSETS: Mapping[str, bytes] = MappingProxyType({})


def native_exam_to_examnet_qti_items(
    document: NativeExamDocument,
    *,
    assets_by_id: Mapping[str, bytes] = NO_EXPORT_ASSETS,
) -> tuple[ExamNetQtiItem, ...]:
    """Convert the native exam to reusable Exam.net QTI items in document order.

    The document outline names each top-level entry in order. A standalone native item
    becomes one QTI item. A part with children and a printed instruction becomes one
    parent QTI item at the part's place; a part whose instruction prints nothing passes
    each child through as a standalone item. A part with no questions and a printed
    instruction becomes an unnumbered information block (G5); a childless part whose
    instruction prints nothing exports nothing.
    """

    assets = {asset.asset_id: asset for asset in document.assets}
    labels = SWEDISH_EXAM_LABELS
    global_stem = document.printed_instructions()
    qti_items: list[ExamNetQtiItem] = []
    for entry in document_outline(document):
        if isinstance(entry, OutlineQuestion):
            qti_items.append(
                _standalone_with_stem(
                    item=entry.item,
                    stem=global_stem,
                    assets=assets,
                    assets_by_id=assets_by_id,
                    labels=labels,
                )
            )
            continue
        if not entry.children:
            if is_empty_body(entry.part.instruction):
                continue
            qti_items.append(
                _information_qti_item(
                    part=entry.part,
                    global_stem=global_stem,
                    assets=assets,
                    assets_by_id=assets_by_id,
                    labels=labels,
                )
            )
            continue
        if is_empty_body(entry.part.instruction):
            qti_items.extend(
                _standalone_with_stem(
                    item=child,
                    stem=global_stem,
                    assets=assets,
                    assets_by_id=assets_by_id,
                    labels=labels,
                )
                for child in entry.children
            )
            continue
        qti_items.append(
            _parent_qti_item(
                parent=entry.part,
                global_stem=global_stem,
                children=entry.children,
                assets=assets,
                assets_by_id=assets_by_id,
                labels=labels,
            )
        )
    return tuple(qti_items)


def _standalone_with_stem(
    *,
    item: NativeExamItem,
    stem: tuple[NativeParagraph, ...],
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
    labels: ExamExportLabels,
) -> ExamNetQtiItem:
    stem_resources = stem_image_resources(
        stem,
        owner_id=item.item_id,
        labels=labels,
        assets=assets,
        assets_by_id=assets_by_id,
    )
    child = leaf_qti_item(
        item=item,
        assets=assets,
        assets_by_id=assets_by_id,
        labels=labels,
        first_image_number=len(stem_resources) + 1,
    )
    if not stem:
        return child
    return replace(
        child,
        prompt_lines=(*body_text_lines(stem), *child.prompt_lines),
        prompt_paragraphs=body_prompt_paragraphs(
            (*stem, *item.body),
            gap_ids=placed_gap_ids(item),
        ),
        image_resources=(*stem_resources, *child.image_resources),
    )


def _parent_qti_item(
    *,
    parent: NativeExamParent,
    global_stem: tuple[NativeParagraph, ...],
    children: tuple[NativeExamItem, ...],
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
    labels: ExamExportLabels,
) -> ExamNetQtiItem:
    stem = (*global_stem, *parent.instruction)
    stem_resources = stem_image_resources(
        stem,
        owner_id=parent.parent_id,
        labels=labels,
        assets=assets,
        assets_by_id=assets_by_id,
    )
    qti_children: list[ExamNetQtiItem] = []
    image_count = len(stem_resources)
    for child in children:
        qti_child = leaf_qti_item(
            item=child,
            assets=assets,
            assets_by_id=assets_by_id,
            labels=labels,
            first_image_number=image_count + 1,
        )
        image_count += len(qti_child.image_resources)
        qti_children.append(qti_child)
    first = qti_children[0]
    parent_id = safe_identifier(parent.parent_id)
    if len(qti_children) == 1 and first.interaction_type not in (
        ExamNetQtiInteractionType.GAP_FILL,
        ExamNetQtiInteractionType.INLINE_CHOICE,
    ):
        # One child has nothing to share: a stem outside its interaction would be
        # rejected, so the instruction joins the child's own prompt.
        return replace(
            first,
            item_id=parent_id,
            prompt_lines=(*body_text_lines(stem), *first.prompt_lines),
            prompt_paragraphs=body_prompt_paragraphs(
                (*stem, *children[0].body), gap_ids=placed_gap_ids(children[0])
            ),
            image_resources=(*stem_resources, *first.image_resources),
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
        prompt_lines=body_text_lines(stem),
        prompt_paragraphs=body_prompt_paragraphs(stem),
        max_score=sum(scored) if scored else None,
        expected_lines=children[0].writing_lines,
        evaluation_mode=(
            ExamNetQtiEvaluationMode.MANUAL_UNKEYED
            if manual
            else ExamNetQtiEvaluationMode.AUTOMATIC
        ),
        image_resources=(
            *stem_resources,
            *(image for child in qti_children for image in child.image_resources),
        ),
        instruction_lines=body_text_lines(stem),
        children=tuple(qti_children),
    )


def _information_qti_item(
    *,
    part: NativeExamParent,
    global_stem: tuple[NativeParagraph, ...],
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
    labels: ExamExportLabels,
) -> ExamNetQtiItem:
    """A childless part's printed instruction as an unnumbered Exam.net information block.

    The body holds the same stem a parent prints (the exam instruction then the part's
    own), one positioned prompt, but no interaction and no score; ``sequence`` is the
    part's stored place so the planner's stable sort keeps it between its neighbours.
    """

    stem = (*global_stem, *part.instruction)
    stem_resources = stem_image_resources(
        stem,
        owner_id=part.parent_id,
        labels=labels,
        assets=assets,
        assets_by_id=assets_by_id,
    )
    return ExamNetQtiItem(
        item_id=safe_identifier(part.parent_id),
        sequence=part.place,
        title="Instruktion",
        interaction_type=ExamNetQtiInteractionType.INFORMATION,
        prompt_lines=body_text_lines(stem),
        prompt_paragraphs=body_prompt_paragraphs(stem),
        max_score=None,
        image_resources=stem_resources,
        instruction_lines=body_text_lines(stem),
    )


def _parent_title(children: tuple[NativeExamItem, ...], labels: ExamExportLabels) -> str:
    """The span of the children's printed labels (D20); running numbers when one lacks it."""
    printed = [child.printed_label for child in children if child.printed_label]
    if len(printed) == len(children):
        return labels.printed_span(printed[0], printed[-1])
    return labels.question_label(children[0].sequence, children[-1].sequence)
