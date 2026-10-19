"""Map one read QTI leaf item to its native item, points and answer key.

``qti_import`` owns package assembly, parents and notes and ``qti_import_body``
owns prompt bodies; this module owns the single authoritative projection for
each leaf interaction kind, including choices, gaps, matching pairs and keys.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_DOWN, Decimal
from typing import Literal, Protocol

from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiMatchEntry,
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
from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    with_settled_points_wording,
)
from skriptoteket.domain.curated_apps.exam_workspace.qti_import_body import (
    label_body,
    paragraphs,
)
from skriptoteket.domain.errors import validation_error

KINDS = {
    ExamNetQtiInteractionType.SINGLE_CHOICE: NativeExamItemKind.SINGLE_CHOICE,
    ExamNetQtiInteractionType.MULTIPLE_RESPONSE: NativeExamItemKind.MULTIPLE_RESPONSE,
    ExamNetQtiInteractionType.GAP_FILL: NativeExamItemKind.GAP_FILL,
    ExamNetQtiInteractionType.INLINE_CHOICE: NativeExamItemKind.INLINE_CHOICE,
    ExamNetQtiInteractionType.FREE_TEXT: NativeExamItemKind.FREE_TEXT,
    ExamNetQtiInteractionType.MATCHING: NativeExamItemKind.MATCHING,
    ExamNetQtiInteractionType.ORDERING: NativeExamItemKind.ORDERING,
}
_CHOICE_KINDS = (NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE)
_PARTIAL_GAP_KEY_REASON = "Facit saknades för en eller flera luckor och importerades inte."
_UNEVEN_MATCH_TICK_REASON = "Poängen kunde inte delas lika mellan paren. Kontrollera poängen."
_MISSING_POINTS_REASON = "Poängen stod inte i paketet. Ange poäng."


class AssetRegistry(Protocol):
    """Collect picture payloads once per deterministic asset id."""

    def register(self, resource: ExamNetQtiImageResource) -> str: ...


def leaf_item(
    source: ExamNetQtiItem,
    *,
    sequence: int,
    assets: AssetRegistry,
) -> NativeExamItem | None:
    """Map one leaf; ``None`` means it cannot be a native item and becomes a note."""

    kind = KINDS[source.interaction_type]
    if not _key_identifiers_are_declared(source, kind):
        return None
    image_ids = tuple(assets.register(resource) for resource in source.image_resources)
    body = paragraphs(
        source.prompt_paragraphs,
        image_ids=image_ids,
        plain_lines=source.prompt_lines,
    )
    reasons: list[str] = []
    points = source.max_score
    tick_points: Decimal | None = None
    writing_lines: int | None = None
    choices: tuple[NativeChoice, ...] = ()
    gaps: tuple[NativeGap, ...] = ()
    print_order: tuple[str, ...] = ()
    match_left: tuple[NativeMatchLeft, ...] = ()
    match_right: tuple[NativeMatchRight, ...] = ()
    answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)
    answer_key_text: str | None = None

    if kind is NativeExamItemKind.FREE_TEXT:
        if source.expected_lines is None:
            return None
        writing_lines = source.expected_lines
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
                body=label_body(by_identifier[identifier], image_ids=image_ids),
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

    if points is None:
        reasons.append(_MISSING_POINTS_REASON)

    try:
        item = NativeExamItem(
            item_id=f"item_{sequence:03d}",
            sequence=sequence,
            kind=kind,
            body=body,
            points=points,
            tick_points=tick_points,
            writing_lines=writing_lines,
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
    return with_settled_points_wording(
        item.model_copy(
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
    )


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
                body=label_body(choice, image_ids=image_ids),
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
                body=label_body(entry, image_ids=image_ids),
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
                body=label_body(entry, image_ids=image_ids),
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


def native_media_type(media_type: str) -> Literal["image/png", "image/jpeg"]:
    if media_type == "image/png":
        return "image/png"
    if media_type == "image/jpeg":
        return "image/jpeg"
    raise validation_error("Bilden har ett format som inte stöds.")
