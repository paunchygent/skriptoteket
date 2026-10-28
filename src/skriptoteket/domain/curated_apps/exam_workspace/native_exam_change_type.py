"""Retype one question without inventing replacement teaching content."""

import random
from dataclasses import dataclass
from decimal import Decimal

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import NativeMatchPair
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_ordering import (
    draw_print_order,
    ordering_points_in_part,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeParseOrigin,
)
from skriptoteket.domain.errors import validation_error

_CHOICE = {NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE}
_GAP = {NativeExamItemKind.GAP_FILL, NativeExamItemKind.INLINE_CHOICE}


@dataclass(frozen=True)
class NativeExamChangeTypeResult:
    document: NativeExamDocument
    dropped_content: tuple[str, ...]


def _empty_body() -> tuple[NativeParagraph, ...]:
    return ()


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


def _without_kept_links(
    body: list[dict[str, object]] | tuple[dict[str, object], ...],
    *,
    gap_ids: set[str] | None = None,
) -> list[dict[str, object]]:
    """Strip kept-gap word links, keeping the visible words and their marks."""
    cleaned_body: list[dict[str, object]] = []
    for paragraph in body:
        raw_segments = paragraph.get("segments")
        if not isinstance(raw_segments, (list, tuple)):
            cleaned_body.append(paragraph)
            continue
        segments: list[dict[str, object]] = []
        for segment in raw_segments:
            if (
                isinstance(segment, dict)
                and segment.get("kind") == "text"
                and segment.get("kept_gap_id") is not None
                and (gap_ids is None or segment.get("kept_gap_id") in gap_ids)
            ):
                segments.append({**segment, "kept_gap_id": None})
            elif isinstance(segment, dict):
                segments.append(segment)
        cleaned_body.append({**paragraph, "segments": segments})
    return cleaned_body


def _kept_gaps_become_options(
    kept_gaps: tuple[NativeGap, ...],
) -> tuple[tuple[NativeGap, ...], set[str]]:
    """Turn kept typed answers into kept dropdown options, like the live gaps.

    Returns the transformed records and the ids of kept gaps without answers,
    which a revert never keeps and which drop with their links.
    """
    transformed: list[NativeGap] = []
    dropped_ids: set[str] = set()
    for gap in kept_gaps:
        if not gap.accepted_values:
            dropped_ids.add(gap.gap_id)
            continue
        transformed.append(
            NativeGap(
                gap_id=gap.gap_id,
                options=_options_from_accepted_values(gap.accepted_values),
                correct_option_id="choice_001",
            )
        )
    return tuple(transformed), dropped_ids


def _rebuild_with_changed_item(
    document: NativeExamDocument, *, item_id: str, changed: NativeExamItem
) -> NativeExamDocument:
    """Return the document with one item replaced, leaving the input untouched."""
    rebuilt = document.model_dump()
    rebuilt["items"] = [
        changed.model_dump() if entry.item_id == item_id else entry.model_dump()
        for entry in document.items
    ]
    return NativeExamDocument.model_validate(rebuilt)


def _place_gap_at_end(body: tuple[NativeParagraph, ...], gap_id: str) -> list[dict[str, object]]:
    """Append a gap at the end of the last question paragraph (D9).

    Trailing paragraphs without segments hold no content, so they drop away
    before the gap is placed; when nothing with content remains, the gap
    paragraph first is followed by an empty paragraph. Otherwise the gap goes
    last in the final paragraph, separated from the text by one unmarked
    ``" "`` unless that paragraph already ends in whitespace or in a non-text
    segment. Earlier paragraphs keep their shape; the paragraph keeps its
    heading level. Mirrors the client's ``withGapTextShape``.
    """
    kept = len(body)
    while kept > 0 and len(body[kept - 1].segments) == 0:
        kept -= 1
    gap_segment: dict[str, object] = {"kind": "gap", "gap_id": gap_id}
    if kept == 0:
        return [
            {"segments": [gap_segment], "heading_level": None},
            {"segments": [], "heading_level": None},
        ]
    last = body[kept - 1]
    trailing = last.segments[-1] if last.segments else None
    separator: list[dict[str, object]] = (
        [{"kind": "text", "text": " ", "marks": ()}]
        if isinstance(trailing, NativeTextSegment)
        and trailing.text
        and not trailing.text[-1].isspace()
        else []
    )
    dumped = last.model_dump()
    kept_segments = dumped["segments"]
    return [
        *(paragraph.model_dump() for paragraph in body[: kept - 1]),
        dict(dumped, segments=[*kept_segments, *separator, gap_segment]),
    ]


def change_item_type(
    document: NativeExamDocument,
    *,
    item_id: str,
    target_kind: NativeExamItemKind,
    rng: random.Random,
) -> NativeExamChangeTypeResult:
    """Retype one question; ``rng`` draws the print order of a new ordering question."""
    in_part = document.parent_of(item_id) is not None
    item = document.item_by_id(item_id)
    fallback = item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    if item.kind == target_kind:
        if not fallback:
            return NativeExamChangeTypeResult(document, ())
        changed_item = item.model_copy(
            update={
                "review": item.review.model_copy(
                    update={"parse_origin": NativeParseOrigin.TEACHER_RETYPED}
                )
            }
        )
        return NativeExamChangeTypeResult(
            _rebuild_with_changed_item(document, item_id=item_id, changed=changed_item), ()
        )
    if target_kind == NativeExamItemKind.MATCHING and item.points is not None:
        points = Decimal(str(item.points))
        exponent = points.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -2:
            raise validation_error(
                "Poängen måste ha högst två decimaler för att frågan ska bli matchning.",
                details={"reason": "matching_points_precision", "item_id": item_id},
            )
    data = item.model_dump()
    if fallback:
        data["review"] = {
            **data["review"],
            "parse_origin": NativeParseOrigin.TEACHER_RETYPED,
        }
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
        and (
            any(
                g.accepted_values or g.automatic_values or g.excluded_automatic_values
                for g in item.gaps
            )
            or (
                target_kind not in _GAP
                and any(
                    gap.accepted_values or gap.automatic_values or gap.excluded_automatic_values
                    for gap in item.kept_gaps
                )
            )
        ),
    )
    drop(
        "options",
        any(g.options for g in item.gaps)
        or (
            target_kind is not NativeExamItemKind.INLINE_CHOICE
            and any(gap.options for gap in item.kept_gaps)
        ),
    )
    drop(
        "correct_option_id",
        any(g.correct_option_id for g in item.gaps)
        or (
            target_kind is not NativeExamItemKind.INLINE_CHOICE
            and any(gap.correct_option_id for gap in item.kept_gaps)
        ),
    )
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
        # Retyping sets the writing area: a new free-text question starts at the
        # house default, and every other kind carries no writing lines (W4).
        writing_lines=(
            DEFAULT_WRITING_LINES if target_kind is NativeExamItemKind.FREE_TEXT else None
        ),
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
            if target_kind == NativeExamItemKind.GAP_FILL:
                data["body"] = _place_gap_at_end(item.body, "gap_001")
            else:
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
    if values_become_options:
        transformed_kept_gaps, dropped_kept_ids = _kept_gaps_become_options(item.kept_gaps)
        data["kept_gaps"] = transformed_kept_gaps
        if dropped_kept_ids:
            data["body"] = _without_kept_links(data["body"], gap_ids=dropped_kept_ids)
    elif item.kept_gaps and target_kind is not NativeExamItemKind.INLINE_CHOICE:
        # Kept answers survive only as kept dropdown options above: every other
        # target drops the hidden records while the words stay as plain text
        # with their marks. Dropdown options never become typed answers.
        data["kept_gaps"] = ()
        data["body"] = _without_kept_links(data["body"])
    if item.kind in _GAP and not keep_gaps:
        # Remove interaction markers, not surrounding teacher text or its formatting.
        body = []
        for paragraph in data["body"]:
            segments = [segment for segment in paragraph["segments"] if segment["kind"] != "gap"]
            if segments:
                body.append(dict(paragraph, segments=segments))
        data["body"] = body or _empty_body()
    changed = NativeExamItem.model_validate(data)
    if in_part and target_kind is NativeExamItemKind.ORDERING:
        # A part child retyped to ordering is worth 1 point in the same result (D1).
        changed = ordering_points_in_part(changed)
    return NativeExamChangeTypeResult(
        _rebuild_with_changed_item(document, item_id=item_id, changed=changed),
        tuple(dropped),
    )
