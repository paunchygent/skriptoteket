"""Shared builders for the split QTI import mapping tests.

Moved unchanged from test_qti_import_mapping.py so the split test modules
import helpers instead of copying them.
"""

import hashlib
from uuid import uuid4

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiInlineChoiceGap,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiMatchPair,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_qti_export import (
    native_exam_to_examnet_qti_items,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.qti_import import (
    build_native_exam_from_qti,
)
from tests.unit.application.curated_apps.qti_round_trip_support import (
    _position,
    _positions,
)

PNG_ONE = b"\x89PNG\r\n\x1a\nfirst picture"
PNG_TWO = b"\x89PNG\r\n\x1a\nsecond picture"
_ASSET_ONE = "asset_1111111111111111"
_ASSET_TWO = "asset_2222222222222222"
_SOURCE_SHA = "a" * 64


def _asset(asset_id: str, payload: bytes) -> NativeExamAsset:
    return NativeExamAsset(
        asset_id=asset_id,
        sha256=hashlib.sha256(payload).hexdigest(),
        media_type="image/png",
        byte_length=len(payload),
    )


def _document(
    items: tuple[NativeExamItem, ...],
    *,
    assets: tuple[NativeExamAsset, ...] = (),
    parents: tuple[NativeExamParent, ...] = (),
) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov på svenska",
        items=items,
        parents=parents,
        assets=assets,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _at(item: NativeExamItem, sequence: int) -> NativeExamItem:
    return NativeExamItem.model_validate(
        {**dict(item), "item_id": f"item_{sequence:03d}", "sequence": sequence}
    )


def _round_trip(
    document: NativeExamDocument,
    payloads: dict[str, bytes] | None = None,
) -> tuple[tuple[ExamNetQtiItem, ...], ExamWorkspaceContainerContent]:
    items = native_exam_to_examnet_qti_items(document, assets_by_id=payloads or {})
    container = build_native_exam_from_qti(
        items=items,
        document_id=uuid4(),
        source_filename="omprov.qti.zip",
        source_sha256=_SOURCE_SHA,
    )
    return items, container


def _qti_item(
    interaction: ExamNetQtiInteractionType,
    *,
    sequence: int,
    opening: str = "Fråga",
    choices: tuple[ExamNetQtiChoice, ...] = (),
    correct_choice_identifiers: tuple[str, ...] = (),
    inline_choice_gaps: tuple[ExamNetQtiInlineChoiceGap, ...] = (),
    match_left: tuple[ExamNetQtiMatchEntry, ...] = (),
    match_right: tuple[ExamNetQtiMatchEntry, ...] = (),
    match_pairs: tuple[ExamNetQtiMatchPair, ...] = (),
    children: tuple[ExamNetQtiItem, ...] = (),
) -> ExamNetQtiItem:
    """A read QTI item built by hand, independent of what the exporter produces."""

    return ExamNetQtiItem(
        item_id=f"item_{sequence:03d}",
        sequence=sequence,
        title=opening,
        interaction_type=interaction,
        prompt_lines=(opening,),
        max_score=1,
        choices=choices,
        correct_choice_identifiers=correct_choice_identifiers,
        inline_choice_gaps=inline_choice_gaps,
        match_left=match_left,
        match_right=match_right,
        match_pairs=match_pairs,
        children=children,
    )


def _imported(*items: ExamNetQtiItem) -> tuple[tuple[NativeExamItem, ...], tuple[str, ...]]:
    container = build_native_exam_from_qti(
        items=items,
        document_id=uuid4(),
        source_filename="robust.zip",
        source_sha256=_SOURCE_SHA,
    )
    return container.document.items, container.notes


def _prompt_projection(item: ExamNetQtiItem) -> tuple[object, ...]:
    return tuple(
        (
            paragraph.heading_level,
            tuple(
                ("text", segment.text, tuple(segment.marks))
                if isinstance(segment, ExamNetQtiPromptText)
                else ("image", segment.image_index)
                if isinstance(segment, ExamNetQtiPromptImage)
                else ("gap", segment.gap_index)
                for segment in paragraph.segments
            ),
        )
        for paragraph in item.prompt_paragraphs
    )


def _deduped(values: tuple[str, ...]) -> tuple[str, ...]:
    kept: list[str] = []
    for value in values:
        stripped = value.strip()
        if stripped and stripped not in kept:
            kept.append(stripped)
    return tuple(kept)


def _qti_projection(item: ExamNetQtiItem) -> dict[str, object]:
    choice_ids = [choice.identifier for choice in item.choices]
    left_ids = [entry.identifier for entry in item.match_left]
    right_ids = [entry.identifier for entry in item.match_right]
    return {
        "interaction": item.interaction_type.value,
        "prompt": _prompt_projection(item),
        "max_score": item.max_score,
        "choices": tuple(choice.text for choice in item.choices),
        "correct": _positions(choice_ids, item.correct_choice_identifiers),
        "gaps": tuple(_deduped(gap.accepted_values) for gap in item.text_entry_gaps),
        "inline": tuple(
            (
                tuple(option.text for option in gap.options),
                _position(
                    [option.identifier for option in gap.options],
                    gap.correct_option_identifier,
                ),
            )
            for gap in item.inline_choice_gaps
        ),
        "match_left": tuple(entry.text for entry in item.match_left),
        "match_right": tuple(entry.text for entry in item.match_right),
        "pairs": tuple(
            (left_ids.index(pair.left_identifier), right_ids.index(pair.right_identifier))
            for pair in item.match_pairs
        ),
        "children": tuple(_qti_projection(child) for child in item.children),
    }


def _export_projection(items: tuple[ExamNetQtiItem, ...]) -> tuple[object, ...]:
    return tuple(_qti_projection(item) for item in items)


def _information_qti_item(sequence: int, lines: tuple[str, ...]) -> ExamNetQtiItem:
    from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
        ExamNetQtiPromptParagraph,
        ExamNetQtiPromptText,
    )

    paragraphs = tuple(
        ExamNetQtiPromptParagraph(
            segments=(ExamNetQtiPromptText(text=line, marks=()),),
            heading_level=None,
        )
        for line in lines
    )
    return ExamNetQtiItem(
        item_id=f"info_{sequence:03d}",
        sequence=sequence,
        title="Instruktion",
        interaction_type=ExamNetQtiInteractionType.INFORMATION,
        prompt_lines=lines,
        max_score=None,
        prompt_paragraphs=paragraphs,
        instruction_lines=lines,
    )
