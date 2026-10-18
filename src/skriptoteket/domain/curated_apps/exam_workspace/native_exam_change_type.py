"""Retype one question without inventing replacement teaching content."""

import random
from dataclasses import dataclass
from decimal import Decimal

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import NativeMatchPair
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_ordering import (
    draw_print_order,
    ordering_inside_parent_error,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
)
from skriptoteket.domain.errors import validation_error

_CHOICE = {NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE}
_GAP = {NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE}


@dataclass(frozen=True)
class NativeExamChangeTypeResult:
    document: NativeExamDocument
    dropped_content: tuple[str, ...]


def _empty_body() -> tuple[NativeParagraph, ...]:
    return (NativeParagraph(segments=(NativeTextSegment(text=" ", marks=()),), heading_level=None),)


def _empty_choices() -> tuple[NativeChoice, ...]:
    return tuple(NativeChoice(choice_id=f"choice_{i:03d}", body=_empty_body()) for i in (1, 2))


def _next_choice_id(choices: tuple[NativeChoice, ...]) -> str:
    used = {choice.choice_id for choice in choices}
    return next(f"choice_{n:03d}" for n in range(1, len(used) + 2) if f"choice_{n:03d}" not in used)


def _options_from_accepted_values(values: tuple[str, ...]) -> tuple[NativeChoice, ...]:
    """Turn a typed gap's accepted values into dropdown options, verbatim and in order."""
    return tuple(
        NativeChoice(
            choice_id=f"choice_{index:03d}",
            body=(
                NativeParagraph(
                    segments=(NativeTextSegment(text=value, marks=()),), heading_level=None
                ),
            ),
        )
        for index, value in enumerate(values, start=1)
    )


def change_item_type(
    document: NativeExamDocument,
    *,
    item_id: str,
    target_kind: NativeExamItemKind,
    rng: random.Random,
) -> NativeExamChangeTypeResult:
    """Retype one question; ``rng`` draws the print order of a new ordering question."""
    if target_kind == NativeExamItemKind.ORDERING and document.parent_of(item_id) is not None:
        raise ordering_inside_parent_error(item_id)
    item = document.item_by_id(item_id)
    if item.kind == target_kind:
        return NativeExamChangeTypeResult(document, ())
    if target_kind == NativeExamItemKind.MATCHING and item.points is not None:
        points = Decimal(str(item.points))
        exponent = points.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise validation_error(
                "Poängen måste ha högst två decimaler för att frågan ska bli matchning.",
                details={"reason": "matching_points_precision", "item_id": item_id},
            )
    data = item.model_dump()
    dropped: list[str] = []

    def drop(name: str, present: bool) -> None:
        if present and name not in dropped:
            dropped.append(name)

    steps_from_choices = item.kind in _CHOICE and target_kind == NativeExamItemKind.ORDERING
    choices_from_steps = item.kind == NativeExamItemKind.ORDERING and target_kind in _CHOICE
    keep_choices = (item.kind in _CHOICE and target_kind in _CHOICE) or (
        steps_from_choices or choices_from_steps
    )
    keep_gaps = item.kind in _GAP and target_kind in _GAP
    drop("choices", bool(item.choices) and not keep_choices)
    keep_key = (
        keep_choices
        and not steps_from_choices
        and not choices_from_steps
        and (
            target_kind != NativeExamItemKind.SINGLE_CHOICE
            or len(item.answer_key.correct_choice_ids) <= 1
        )
    )
    drop("correct_choice_ids", bool(item.answer_key.correct_choice_ids) and not keep_key)
    drop("gaps", bool(item.gaps) and not keep_gaps)
    # Accepted values become dropdown options; misspelling lists are dropped silently.
    values_become_options = (
        item.kind == NativeExamItemKind.GAP_FILL and target_kind == NativeExamItemKind.INLINE_CHOICE
    )
    drop(
        "accepted_values",
        not values_become_options
        and any(
            g.accepted_values or g.automatic_values or g.excluded_automatic_values
            for g in item.gaps
        ),
    )
    drop("options", any(g.options for g in item.gaps))
    drop("correct_option_id", any(g.correct_option_id for g in item.gaps))
    for name in ("match_left", "match_right", "criteria"):
        drop(name, bool(getattr(item, name)))
        data[name] = ()
    drop("match_pairs", bool(item.answer_key.match_pairs))
    drop("tick_points", item.tick_points is not None)
    drop("ai_suggestion", item.ai_suggestion is not None)
    data.update(
        kind=target_kind,
        choices=(),
        gaps=(),
        tick_points=None,
        ai_suggestion=None,
        print_order=(),
    )
    if target_kind == item.suggested_kind:
        data["suggested_kind"] = None
    key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.ABSENT)
    if target_kind in _CHOICE:
        data["choices"] = item.choices if keep_choices else _empty_choices()
        if choices_from_steps and len(item.choices) < 2:
            data["choices"] = (
                *item.choices,
                NativeChoice(choice_id=_next_choice_id(item.choices), body=_empty_body()),
            )
        if keep_key:
            key = item.answer_key
    elif target_kind == NativeExamItemKind.ORDERING:
        steps = item.choices if steps_from_choices else _empty_choices()
        data["choices"] = steps
        data["print_order"] = draw_print_order([step.choice_id for step in steps], rng)
        key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED)
        if item.points is None:
            data["points"] = 1
            data["points_estimated"] = False
    elif target_kind == NativeExamItemKind.FREE_TEXT:
        key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE)
    elif target_kind in _GAP:
        gap_ids = tuple(gap.gap_id for gap in item.gaps) if keep_gaps else ("gap_001",)
        seeds = (
            {gap.gap_id: gap.accepted_values for gap in item.gaps} if values_become_options else {}
        )
        data["gaps"] = tuple(
            NativeGap(
                gap_id=gap_id,
                options=(
                    (_options_from_accepted_values(seeds.get(gap_id, ())) or _empty_choices())
                    if target_kind == NativeExamItemKind.INLINE_CHOICE
                    else ()
                ),
                correct_option_id=(
                    "choice_001" if target_kind == NativeExamItemKind.INLINE_CHOICE else None
                ),
            )
            for gap_id in gap_ids
        )
        if target_kind == NativeExamItemKind.INLINE_CHOICE:
            kept_origin = item.answer_key.origin
            key = NativeAnswerKey(
                origin=(
                    kept_origin
                    if values_become_options and kept_origin != NativeAnswerKeyOrigin.ABSENT
                    else NativeAnswerKeyOrigin.TEACHER_AUTHORED
                )
            )
        if not keep_gaps:
            data["body"] = [
                *data["body"],
                {"segments": [{"kind": "gap", "gap_id": "gap_001"}], "heading_level": None},
            ]
    elif target_kind == NativeExamItemKind.MATCHING:
        # A grid needs two columns, but only one correct pair. Empty labels block export.
        data["match_left"] = [{"left_id": "left_001", "body": _empty_body()}]
        data["match_right"] = [
            {"right_id": f"right_{i:03d}", "body": _empty_body()} for i in (1, 2)
        ]
        data["tick_points"] = Decimal(str(item.points)) if item.points is not None else Decimal(0)
        if item.points is not None:
            key = NativeAnswerKey(
                origin=NativeAnswerKeyOrigin.TEACHER_AUTHORED,
                match_pairs=(NativeMatchPair(left_id="left_001", right_id="right_001"),),
            )
    data["answer_key"] = key
    if item.kind in _GAP and not keep_gaps:
        # Remove interaction markers, not surrounding teacher text or its formatting.
        body = []
        for paragraph in data["body"]:
            segments = [segment for segment in paragraph["segments"] if segment["kind"] != "gap"]
            if segments:
                body.append(dict(paragraph, segments=segments))
        data["body"] = body or _empty_body()
    changed = NativeExamItem.model_validate(data)
    rebuilt = document.model_dump()
    rebuilt["items"] = [
        changed.model_dump() if entry.item_id == item_id else entry.model_dump()
        for entry in document.items
    ]
    return NativeExamChangeTypeResult(NativeExamDocument.model_validate(rebuilt), tuple(dropped))
