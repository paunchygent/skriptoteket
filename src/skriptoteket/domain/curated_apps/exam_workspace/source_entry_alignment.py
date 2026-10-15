"""One monotone token alignment for every native entry surface.

A single shortest-path search walks the source token index. A state is the
current source token, one next-entry ordinal per surface, and the active
entry's wording cursor. Matching, adopting a printed label and skipping optional score annotations
are free; substituting, inserting visible content, deleting, leaving visible
source tokens unowned and leaving an entry unassigned have positive costs.
An exact copy is therefore reached first, and a rewrite stays on the same path
instead of a second algorithm.
Completing an active entry consumes its contiguous token interval and exposes
the next ordinal of that surface.

The search never enumerates occurrences, certificate walks or ordinal/source
end products: one memoised best state and predecessor per reached state, with
the deepest progress expanded first. A state is only merged with an equally
reached one, and the completion rule reads the state itself, so dominance never
depends on how the active interval began.
"""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_labels import LabelOption
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_tokens import (
    SourceToken,
    source_tokens,
    wording_tokens,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    NativeSourceEntry,
    entry_source_extent,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting

# Lexicographic path cost: unassigned entries, edit distance, then label-family
# preference. Every increment is non-negative, so the first completed state the
# search pops is the best one.
_Cost = tuple[int, int, int]
_ZERO: _Cost = (0, 0, 0)
_SKIP_ENTRY: _Cost = (1, 0, 0)
_SUBSTITUTE: _Cost = (0, 5, 0)
_DELETE: _Cost = (0, 4, 0)
_INSERT: _Cost = (0, 3, 0)
_UNOWNED: _Cost = (0, 2, 0)

_Active = tuple[int, bool, int, bool]
_Key = tuple[int, tuple[int, ...], _Active | None]


def entry_unit_bounds(source: SourceFormatting, start: int) -> tuple[int, int]:
    """The entry's paragraph, physical line or table cell envelope."""
    return entry_source_extent(
        source, NativeSourceEntry("", 1, start, min(start + 1, len(source.text)))
    )


def _label_preference(sequence: str, text: str, label_start: int) -> int:
    """A soft label-family preference; source order still assigns other layouts."""
    at = label_start
    while at < len(text) and text[at].isspace():
        at += 1
    if at < len(text) and text[at] in "([{":
        at += 1
    token = text[at] if at < len(text) else ""
    if sequence == "match_left":
        return 0 if token.isdigit() else 1
    if sequence == "match_right":
        return 0 if token.isalpha() else 1
    return 0


@dataclass(frozen=True, slots=True)
class EntryAnchor:
    """One entry's complete aligned source content inside the shared partition.

    ``start``/``end`` are the consumed token interval's character span, with a
    printed label included when the entry adopted one. ``anchor_start`` and
    ``anchor_end`` locate the wording evidence inside that span, or ``(-1, -1)``
    when the wording was rewritten away from any verbatim occurrence.
    """

    surface_index: int
    ordinal: int
    start: int
    end: int
    anchor_start: int
    anchor_end: int
    label_start: int | None
    exact: bool


def _add(cost: _Cost, addition: _Cost) -> _Cost:
    return (cost[0] + addition[0], cost[1] + addition[1], cost[2] + addition[2])


def _available(token: SourceToken, blocked: tuple[tuple[int, int], ...]) -> bool:
    return not any(token.start < end and start < token.end for start, end in blocked)


def _word_token(value: str) -> bool:
    return value[0].isalnum() or value[0] == "_"


def align_entries(
    text: str,
    sequences: tuple[str, ...],
    texts: tuple[tuple[str, ...], ...],
    *,
    labels: dict[tuple[int, int], tuple[LabelOption, ...]] | None = None,
    blocked: tuple[tuple[int, int], ...] = (),
) -> dict[tuple[int, int], EntryAnchor]:
    """Allocate every entry a disjoint ordered source interval in one search.

    State keys are ``(token index, progress per surface, active)``. The active
    part is ``None``, or ``(surface index, label adopted, wording cursor,
    consumed a source token)``. Two paths reaching one state keep only the
    cheaper cost, because no remaining transition depends on how the active
    interval began.
    """
    tokens = source_tokens(text)
    available = tuple(_available(token, blocked) for token in tokens)
    # Optional metadata is neutral alignment material, not an edit to visible
    # wording. This changes search costs only; provenance decides exclusion.
    annotations = tuple((m.start(), m.end()) for m in POINT_LABEL.finditer(text))
    annotation_index = 0
    neutral_tokens: list[bool] = []
    for token in tokens:
        while (
            annotation_index < len(annotations) and annotations[annotation_index][1] <= token.start
        ):
            annotation_index += 1
        neutral_tokens.append(
            annotation_index < len(annotations)
            and annotations[annotation_index][0] <= token.start
            and token.end <= annotations[annotation_index][1]
        )
    neutral = tuple(neutral_tokens)
    wordings = tuple(tuple(wording_tokens(value) for value in surface) for surface in texts)
    counts = tuple(len(surface) for surface in texts)
    surfaces = len(texts)
    by_token: dict[int, list[tuple[int, int, LabelOption]]] = {}
    preference_floor: list[list[int]] = []
    options_by_entry = labels or {}
    for (index, ordinal), options in options_by_entry.items():
        for option in options:
            by_token.setdefault(option.first_token, []).append((index, ordinal, option))
    for index in range(surfaces):
        floor = [0] * (counts[index] + 1)
        for ordinal in range(counts[index], 0, -1):
            values = options_by_entry.get((index, ordinal))
            lowest = (
                min(_label_preference(sequences[index], text, option.start) for option in values)
                if values
                else 2
            )
            floor[ordinal - 1] = floor[ordinal] + lowest
        preference_floor.append(floor)
    structural = {option.first_token for options in options_by_entry.values() for option in options}
    paragraph_starts = {
        index
        for index in range(1, len(tokens))
        if "\n" in text[tokens[index - 1].end : tokens[index].start]
    }
    available_suffix = [0] * (len(tokens) + 1)
    for index in range(len(tokens) - 1, -1, -1):
        available_suffix[index] = available_suffix[index + 1] + (1 if available[index] else 0)
    start_key: _Key = (0, (0,) * surfaces, None)
    best: dict[_Key, _Cost] = {start_key: _ZERO}
    previous: dict[_Key, _Key] = {}
    active_origin: dict[_Key, tuple[int, int | None, int]] = {start_key: (0, None, 0)}
    counter = 0

    def estimate(key: _Key, cost: _Cost) -> tuple:
        """Admissible remaining-cost bound so the deepest zero-cost path wins.

        Pending entries still pay their lowest possible label preference, and a
        pending entry that cannot even claim an available source token must be
        skipped. Both are lower bounds on every completion of this state.
        """
        token_index, progress, active = key
        pending = 0
        preference = 0
        for index in range(surfaces):
            used = progress[index]
            if active is not None and active[0] == index:
                used += 1
            pending += counts[index] - used
            preference += preference_floor[index][used]
        skipped = max(0, pending - available_suffix[token_index])
        # Unavoidably skipped entries pay no label preference. Subtract their
        # largest possible preference so this stays a lower bound even when
        # the model produced more entries than there are source tokens.
        bound = (
            cost[0] + skipped,
            cost[1],
            cost[2] + max(0, preference - 2 * skipped),
        )
        return (bound, -sum(progress), -token_index, 0, key, cost)

    heap: list[tuple] = [estimate(start_key, _ZERO)]

    def relax(
        key: _Key,
        cost: _Cost,
        target: _Key,
        addition: _Cost,
        origin: tuple[int, int | None, int] | None = None,
    ) -> None:
        nonlocal counter
        target_cost = _add(cost, addition)
        seen = best.get(target)
        if seen is not None and seen <= target_cost:
            return
        best[target] = target_cost
        previous[target] = key
        if origin is not None:
            active_origin[target] = origin
        elif target[2] is not None:
            active_origin[target] = active_origin[key]
        counter += 1
        bound, neg_depth, neg_token, _, _, _linked = estimate(target, target_cost)
        heappush(heap, (bound, neg_depth, neg_token, counter, target, target_cost))

    goal: _Key | None = None
    while heap:
        _bound, _neg_depth, _neg_token, _serial, key, cost = heappop(heap)
        if best.get(key) != cost:
            continue
        token_index, progress, active = key
        if active is None and progress == counts and token_index == len(tokens):
            goal = key
            break
        if active is None:
            if token_index < len(tokens):
                relax(
                    key,
                    cost,
                    (token_index + 1, progress, None),
                    _ZERO if not available[token_index] or neutral[token_index] else _UNOWNED,
                )
            for index in range(surfaces):
                ordinal = progress[index] + 1
                if ordinal > counts[index]:
                    continue
                if not wordings[index][ordinal - 1]:
                    continue
                if token_index < len(tokens) and available[token_index]:
                    relax(
                        key,
                        cost,
                        (token_index, progress, (index, False, 0, False)),
                        (0, 0, 2),
                        (token_index, None, 0),
                    )
                for owner_index, owner_ordinal, option in by_token.get(token_index, ()):
                    if owner_index != index or owner_ordinal != ordinal:
                        continue
                    stop = token_index + option.token_count
                    if stop > len(tokens) or not all(available[token_index:stop]):
                        continue
                    relax(
                        key,
                        cost,
                        (stop, progress, (index, True, 0, False)),
                        (0, 0, _label_preference(sequences[index], text, option.start)),
                        (token_index, option.start, option.token_count),
                    )
            for index in range(surfaces):
                ordinal = progress[index] + 1
                if ordinal > counts[index]:
                    continue
                updated = progress[:index] + (ordinal,) + progress[index + 1 :]
                relax(key, cost, (token_index, updated, None), _SKIP_ENTRY)
            continue
        index, has_label, cursor, consumed = active
        ordinal = progress[index] + 1
        wanted = wordings[index][ordinal - 1]
        length = len(wanted)
        if token_index < len(tokens) and available[token_index]:
            crossing: _Cost = (
                (
                    (0, 8, 0)
                    if token_index in structural
                    else (0, 1, 0)
                    if token_index in paragraph_starts
                    else _ZERO
                )
                if consumed
                else _ZERO
            )
            if cursor < length and tokens[token_index].folded == wanted[cursor]:
                relax(
                    key,
                    cost,
                    (token_index + 1, progress, (index, has_label, cursor + 1, True)),
                    _ZERO,
                )
            if cursor < length and (
                _word_token(tokens[token_index].folded) == _word_token(wanted[cursor])
            ):
                relax(
                    key,
                    cost,
                    (token_index + 1, progress, (index, has_label, cursor + 1, True)),
                    _add(_SUBSTITUTE, crossing),
                )
            relax(
                key,
                cost,
                (token_index + 1, progress, (index, has_label, cursor, True)),
                _add(_ZERO if neutral[token_index] else _INSERT, crossing),
            )
        if cursor < length:
            relax(
                key,
                cost,
                (token_index, progress, (index, has_label, cursor + 1, consumed)),
                _DELETE,
            )
        if cursor == length and consumed:
            updated = progress[:index] + (ordinal,) + progress[index + 1 :]
            relax(key, cost, (token_index, updated, None), _ZERO)

    if goal is None:
        return {}
    chain: list[_Key] = []
    key = goal
    while key != start_key:
        key = previous[key]
        chain.append(key)
    chain.reverse()
    result: dict[tuple[int, int], EntryAnchor] = {}
    for origin in chain:
        active = origin[2]
        if active is None:
            continue
        token_index, progress, _active = origin
        index, _has_label, cursor, _consumed = active
        ordinal = progress[index] + 1
        wanted = wordings[index][ordinal - 1]
        if cursor != len(wanted):
            continue
        start_token, label_char, label_count = active_origin[origin]
        region = tokens[start_token + label_count : token_index]
        if region:
            source_span = text[region[0].start : region[-1].end]
            exact = " ".join(source_span.split()) == " ".join(texts[index][ordinal - 1].split())
        else:
            exact = False
        if label_char is not None:
            anchor = (region[0].start, region[-1].end) if exact else (-1, -1)
            start = label_char
        else:
            anchor = (tokens[start_token].start, tokens[token_index - 1].end)
            start = tokens[start_token].start
        result[index, ordinal] = EntryAnchor(
            surface_index=index,
            ordinal=ordinal,
            start=start,
            end=tokens[token_index - 1].end,
            anchor_start=anchor[0],
            anchor_end=anchor[1],
            label_start=label_char,
            exact=exact,
        )
    return result
