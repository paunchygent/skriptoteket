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
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal
from hashlib import sha256
from pathlib import PurePath
from typing import Literal
from uuid import UUID

from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptSegment,
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
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamHeader,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamAnswerKeyStep,
    NativeExamChosenTypeStep,
    NativeExamImportRecord,
    NativeExamOriginalWording,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_parent import NativeExamParent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_asset_ids
from skriptoteket.domain.errors import validation_error

_KINDS = {
    ExamNetQtiInteractionType.SINGLE_CHOICE: NativeExamItemKind.SINGLE_CHOICE,
    ExamNetQtiInteractionType.MULTIPLE_RESPONSE: NativeExamItemKind.MULTIPLE_RESPONSE,
    ExamNetQtiInteractionType.GAP_FILL: NativeExamItemKind.GAP_FILL,
    ExamNetQtiInteractionType.INLINE_CHOICE: NativeExamItemKind.INLINE_CHOICE,
    ExamNetQtiInteractionType.FREE_TEXT: NativeExamItemKind.FREE_TEXT,
    ExamNetQtiInteractionType.MATCHING: NativeExamItemKind.MATCHING,
    ExamNetQtiInteractionType.ORDERING: NativeExamItemKind.ORDERING,
}
_CHOICE_KINDS = (NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE)
_UNSUPPORTED_NOTES = {
    ExamNetQtiUnsupportedReason.INTERACTION: ("frågetypen stöds inte och importerades inte."),
    ExamNetQtiUnsupportedReason.IMAGE: (
        "en bild i frågan kunde inte läsas och frågan importerades inte."
    ),
}
_PARTIAL_GAP_KEY_REASON = "Facit saknades för en eller flera luckor och importerades inte."
_UNEVEN_MATCH_TICK_REASON = "Poängen kunde inte delas lika mellan paren. Kontrollera poängen."


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
                media_type=_native_media_type(resource.media_type),
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
        if source.children:
            _append_parent(
                source,
                native_items=native_items,
                parents=parents,
                notes=notes,
                assets=assets,
            )
            continue
        leaf = _leaf_item(source, sequence=len(native_items) + 1, assets=assets)
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
        if _KINDS[child.interaction_type] is NativeExamItemKind.ORDERING:
            # Ordering questions are standalone only; a parent cannot hold one.
            notes.append(_interaction_note(child.sequence, _opening_text(child)))
            continue
        leaf = _leaf_item(child, sequence=len(native_items) + 1, assets=assets)
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
    instruction = _paragraphs(
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


def _leaf_item(
    source: ExamNetQtiItem,
    *,
    sequence: int,
    assets: _AssetRegistry,
) -> NativeExamItem | None:
    """Map one leaf; ``None`` means it cannot be a native item and becomes a note."""

    kind = _KINDS[source.interaction_type]
    if not _key_identifiers_are_declared(source, kind):
        return None
    image_ids = tuple(assets.register(resource) for resource in source.image_resources)
    body = _paragraphs(
        source.prompt_paragraphs,
        image_ids=image_ids,
        plain_lines=source.prompt_lines,
    )
    reasons: list[str] = []
    points = source.max_score
    tick_points: Decimal | None = None
    choices: tuple[NativeChoice, ...] = ()
    gaps: tuple[NativeGap, ...] = ()
    print_order: tuple[str, ...] = ()
    match_left: tuple[NativeMatchLeft, ...] = ()
    match_right: tuple[NativeMatchRight, ...] = ()
    answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)
    answer_key_text: str | None = None

    if kind is NativeExamItemKind.FREE_TEXT:
        answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE)
    elif kind in _CHOICE_KINDS:
        choices, choice_ids = _choices(source.choices, image_ids=image_ids)
        correct_ids = tuple(
            choice_ids[identifier] for identifier in source.correct_choice_identifiers
        )
        if correct_ids:
            answer_key = NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                correct_choice_ids=correct_ids,
            )
            labels = {choice.identifier: choice.text for choice in source.choices}
            answer_key_text = "\n".join(
                labels[identifier] for identifier in source.correct_choice_identifiers
            )
        else:
            answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)
    elif kind is NativeExamItemKind.ORDERING:
        by_identifier = {choice.identifier: choice for choice in source.choices}
        key_ids = {
            identifier: f"choice_{index:03d}"
            for index, identifier in enumerate(source.correct_choice_identifiers, start=1)
        }
        choices = tuple(
            NativeChoice(
                choice_id=key_ids[identifier],
                body=_label_body(by_identifier[identifier], image_ids=image_ids),
            )
            for identifier in source.correct_choice_identifiers
        )
        print_order = tuple(key_ids[choice.identifier] for choice in source.choices)
        answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED)
        answer_key_text = "\n".join(
            by_identifier[identifier].text for identifier in source.correct_choice_identifiers
        )
    elif kind is NativeExamItemKind.GAP_FILL:
        gaps = tuple(
            NativeGap(
                gap_id=f"gap_{index:03d}",
                accepted_values=_accepted_values(entry.accepted_values),
            )
            for index, entry in enumerate(source.text_entry_gaps, start=1)
        )
        keyed = [bool(gap.accepted_values) for gap in gaps]
        if all(keyed):
            answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED)
            answer_key_text = "\n".join(value for gap in gaps for value in gap.accepted_values)
        elif any(keyed):
            reasons.append(_PARTIAL_GAP_KEY_REASON)
            gaps = tuple(gap.model_copy(update={"accepted_values": ()}) for gap in gaps)
            answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)
        else:
            answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)
    elif kind is NativeExamItemKind.INLINE_CHOICE:
        mapped_gaps: list[NativeGap] = []
        correct_labels: list[str] = []
        for index, entry in enumerate(source.inline_choice_gaps, start=1):
            options, option_ids = _choices(entry.options, image_ids=image_ids)
            mapped_gaps.append(
                NativeGap(
                    gap_id=f"gap_{index:03d}",
                    options=options,
                    correct_option_id=option_ids[entry.correct_option_identifier],
                )
            )
            correct_labels.append(
                next(
                    option.text
                    for option in entry.options
                    if option.identifier == entry.correct_option_identifier
                )
            )
        gaps = tuple(mapped_gaps)
        answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED)
        answer_key_text = "\n".join(correct_labels)
    else:
        match_left, left_ids = _match_left(source.match_left, image_ids=image_ids)
        match_right, right_ids = _match_right(source.match_right, image_ids=image_ids)
        pairs = tuple(
            NativeMatchPair(
                left_id=left_ids[pair.left_identifier],
                right_id=right_ids[pair.right_identifier],
            )
            for pair in source.match_pairs
        )
        tick_points = Decimal("1")
        if pairs and points is not None:
            tick_points = (Decimal(str(points)) / len(pairs)).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )
            total = tick_points * len(pairs)
            if total != Decimal(str(points)):
                points = _number(total)
                reasons.append(_UNEVEN_MATCH_TICK_REASON)
        if pairs:
            answer_key = NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED,
                match_pairs=pairs,
            )
            answer_key_text = "\n".join(
                f"{pair.left_text} – {pair.right_text}" for pair in source.match_pairs
            )
        else:
            points = None
            answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)

    try:
        item = NativeExamItem(
            item_id=f"item_{sequence:03d}",
            sequence=sequence,
            kind=kind,
            body=body,
            points=points,
            tick_points=tick_points,
            choices=choices,
            print_order=print_order,
            gaps=gaps,
            match_left=match_left,
            match_right=match_right,
            answer_key=answer_key,
            review=NativeItemReview(
                state=(
                    NativeItemReviewState.REVIEW_REQUIRED
                    if reasons
                    else NativeItemReviewState.REVIEW_COMPLETE
                ),
                parse_origin=NativeParseOrigin.DETERMINISTIC,
                reasons=tuple(reasons),
            ),
        )
    except ValidationError:
        return None
    return item.model_copy(
        update={
            "import_record": NativeExamImportRecord(
                original_wording=NativeExamOriginalWording(
                    question_text="\n".join(item.plain_text_lines()),
                    answer_key_text=answer_key_text,
                ),
                steps=(
                    NativeExamChosenTypeStep(chosen_kind=kind),
                    NativeExamAnswerKeyStep(origin=answer_key.origin),
                ),
            )
        }
    )


def _paragraphs(
    paragraphs: tuple[ExamNetQtiPromptParagraph, ...],
    *,
    image_ids: Sequence[str],
    plain_lines: tuple[str, ...],
) -> tuple[NativeParagraph, ...]:
    if not paragraphs:
        return tuple(_plain_paragraph(line) for line in plain_lines)
    return tuple(
        NativeParagraph(
            heading_level=paragraph.heading_level,
            segments=tuple(_segment(segment, image_ids) for segment in paragraph.segments),
        )
        for paragraph in paragraphs
    )


def _segment(
    segment: ExamNetQtiPromptSegment,
    image_ids: Sequence[str],
) -> NativeTextSegment | NativeAssetSegment | NativeGapSegment:
    if isinstance(segment, ExamNetQtiPromptText):
        return NativeTextSegment(text=segment.text, marks=segment.marks)
    if isinstance(segment, ExamNetQtiPromptImage):
        return NativeAssetSegment(asset_id=image_ids[segment.image_index])
    return NativeGapSegment(gap_id=f"gap_{segment.gap_index + 1:03d}")


def _plain_paragraph(text: str) -> NativeParagraph:
    return NativeParagraph(
        heading_level=None,
        segments=(NativeTextSegment(text=text, marks=()),),
    )


def _label_body(
    choice: ExamNetQtiChoice | ExamNetQtiMatchEntry,
    *,
    image_ids: Sequence[str],
) -> tuple[NativeParagraph, ...]:
    if choice.body:
        return _paragraphs(choice.body, image_ids=image_ids, plain_lines=())
    return (_plain_paragraph(choice.text),)


def _choices(
    choices: tuple[ExamNetQtiChoice, ...],
    *,
    image_ids: Sequence[str],
) -> tuple[tuple[NativeChoice, ...], dict[str, str]]:
    ids = {choice.identifier: f"choice_{index:03d}" for index, choice in enumerate(choices, 1)}
    return (
        tuple(
            NativeChoice(
                choice_id=ids[choice.identifier],
                body=_label_body(choice, image_ids=image_ids),
            )
            for choice in choices
        ),
        ids,
    )


def _match_left(
    entries: tuple[ExamNetQtiMatchEntry, ...],
    *,
    image_ids: Sequence[str],
) -> tuple[tuple[NativeMatchLeft, ...], dict[str, str]]:
    ids = {entry.identifier: f"left_{index:03d}" for index, entry in enumerate(entries, 1)}
    return (
        tuple(
            NativeMatchLeft(
                left_id=ids[entry.identifier],
                body=_label_body(entry, image_ids=image_ids),
            )
            for entry in entries
        ),
        ids,
    )


def _match_right(
    entries: tuple[ExamNetQtiMatchEntry, ...],
    *,
    image_ids: Sequence[str],
) -> tuple[tuple[NativeMatchRight, ...], dict[str, str]]:
    ids = {entry.identifier: f"right_{index:03d}" for index, entry in enumerate(entries, 1)}
    return (
        tuple(
            NativeMatchRight(
                right_id=ids[entry.identifier],
                body=_label_body(entry, image_ids=image_ids),
            )
            for entry in entries
        ),
        ids,
    )


def _accepted_values(values: tuple[str, ...]) -> tuple[str, ...]:
    accepted: list[str] = []
    for value in values:
        stripped = value.strip()
        if stripped and stripped not in accepted:
            accepted.append(stripped)
    return tuple(accepted)


def _key_identifiers_are_declared(source: ExamNetQtiItem, kind: NativeExamItemKind) -> bool:
    """Whether every answer-key identifier names an identifier the item declares.

    A package from another producer can key an identifier the item never declares;
    building that item's ids then raises ``KeyError``. Such an item cannot become a
    native item, so the caller turns it into a note instead.
    """

    if kind is NativeExamItemKind.ORDERING:
        return _ordering_key_names_every_step(source)
    if kind in _CHOICE_KINDS:
        declared = {choice.identifier for choice in source.choices}
        return all(identifier in declared for identifier in source.correct_choice_identifiers)
    if kind is NativeExamItemKind.INLINE_CHOICE:
        return all(
            entry.correct_option_identifier in {option.identifier for option in entry.options}
            for entry in source.inline_choice_gaps
        )
    if kind is NativeExamItemKind.MATCHING:
        left = {entry.identifier for entry in source.match_left}
        right = {entry.identifier for entry in source.match_right}
        return all(
            pair.left_identifier in left and pair.right_identifier in right
            for pair in source.match_pairs
        )
    return True


def _ordering_key_names_every_step(item: ExamNetQtiItem) -> bool:
    shown = [choice.identifier for choice in item.choices]
    key = list(item.correct_choice_identifiers)
    return len(shown) == len(set(shown)) and sorted(shown) == sorted(key)


def _number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _native_media_type(media_type: str) -> Literal["image/png", "image/jpeg"]:
    if media_type == "image/png":
        return "image/png"
    if media_type == "image/jpeg":
        return "image/jpeg"
    raise validation_error("Bilden har ett format som inte stöds.")
