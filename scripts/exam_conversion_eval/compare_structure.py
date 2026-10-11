"""Principles 1, 3 and 8: which text and which slots a question holds, and where.

Every gold line and table cell is a phrase. A phrase must be present in the question, once per
gold occurrence and in gold order; a phrase holding gaps must hold them in the same place.
"""

from __future__ import annotations

from collections.abc import Sequence

from .compare_questions import GoldQuestion, Question
from .compare_results import FieldMismatch
from .compare_text import Piece, end_of, occurrences, pieces, stream, words


def membership_groups(parents: Sequence[int | None]) -> list[frozenset[int] | None]:
    """For each question position, the positions of the questions under the same parent."""
    members: dict[int, set[int]] = {}
    for position, parent in enumerate(parents):
        if parent is not None:
            members.setdefault(parent, set()).add(position)
    return [None if parent is None else frozenset(members[parent]) for parent in parents]


def parent_membership(
    gold: frozenset[int] | None, actual: frozenset[int] | None
) -> list[FieldMismatch]:
    """A child sits under the parent that holds its gold siblings, or under none."""
    if gold == actual:
        return []
    return [
        FieldMismatch(
            "segmentation",
            "parent_membership",
            None if gold is None else sorted(gold),
            None if actual is None else sorted(actual),
        )
    ]


def _count_streams(question: Question) -> list[str]:
    """Each place of a question's text that is searched on its own: no phrase spans two."""
    return [
        stream([question.title]),
        stream(question.instruction),
        stream(question.body),
        *(stream([entry]) for entry in question.entries()),
    ]


def _count(streams: Sequence[str], phrase: str) -> int:
    return sum(occurrences(text, phrase) for text in streams)


def _gold_phrases(view: Question) -> tuple[tuple[Piece, ...], tuple[Piece, ...]]:
    return pieces(view.instruction), pieces(view.body)


def all_phrases(questions: Sequence[GoldQuestion]) -> tuple[str, ...]:
    """Every distinct plain phrase of the gold exam's instructions and prompts."""
    found: dict[str, None] = {}
    for question in questions:
        for piece in (*pieces(question.view.instruction), *pieces(question.view.body)):
            if piece.plain:
                found[piece.plain] = None
    return tuple(found)


def _out_of_order(gold_body: Sequence[Piece], native_title: str, native_body: str) -> list[str]:
    """Gold body phrases found in the native body only before the point the walk has reached.

    A phrase found in the title leaves the walk where it is, so a heading may sit in either.
    """
    cursor = 0
    misplaced: list[str] = []
    for piece in gold_body:
        if not piece.plain or end_of(native_title, piece.plain) >= 0:
            continue
        end = end_of(native_body, piece.plain, cursor)
        if end >= 0:
            cursor = end
        elif end_of(native_body, piece.plain) >= 0:
            misplaced.append(piece.plain)
    return misplaced


def segmentation(
    gold: GoldQuestion, actual: Question, phrases: Sequence[str]
) -> list[FieldMismatch]:
    """Principle 1 inside a question: nothing duplicated, reordered or from another question."""
    view = gold.view
    gold_instruction, gold_body = _gold_phrases(view)
    gold_streams, native_streams = _count_streams(view), _count_streams(actual)
    mismatches: list[FieldMismatch] = []
    own = tuple(dict.fromkeys(p.plain for p in (*gold_instruction, *gold_body) if p.plain))
    duplicated = tuple(
        phrase for phrase in own if _count(native_streams, phrase) > _count(gold_streams, phrase)
    )
    if duplicated:
        mismatches.append(FieldMismatch("segmentation", "duplicated_text", (), duplicated))
    misplaced = _out_of_order(gold_body, native_streams[0], native_streams[2])
    if misplaced:
        mismatches.append(FieldMismatch("segmentation", "out_of_order", (), tuple(misplaced)))
    foreign = tuple(
        phrase
        for phrase in phrases
        if _count(gold_streams, phrase) == 0 and _count(native_streams, phrase) > 0
    )
    if foreign:
        mismatches.append(FieldMismatch("segmentation", "foreign_text", (), foreign))
    return mismatches


def _located(actual: Question, piece: Piece, *, instruction: bool, gaps: bool) -> bool:
    """The phrase is in the native instruction, or for a prompt phrase in any of its texts."""
    phrase = piece.gapped if gaps else piece.plain
    texts = (
        (actual.instruction,) if instruction else (actual.body, [actual.title], actual.instruction)
    )
    return any(end_of(stream(text, gaps=gaps), phrase) >= 0 for text in texts)


def content(gold: GoldQuestion, actual: Question) -> list[FieldMismatch]:
    """Principle 8: all gold wording is present, the parent's instruction in the parent."""
    gold_instruction, gold_body = _gold_phrases(gold.view)
    missing = tuple(
        piece.plain
        for instruction, group in ((True, gold_instruction), (False, gold_body))
        for piece in group
        if piece.plain and not _located(actual, piece, instruction=instruction, gaps=False)
    )
    if missing:
        return [FieldMismatch("content_present", "missing_wording", missing, ())]
    return []


def slots(gold: GoldQuestion, actual: Question) -> list[FieldMismatch]:
    """Principle 3: the same gaps in number and place, the same options and the same lists."""
    view = gold.view
    mismatches: list[FieldMismatch] = []
    if len(view.gaps) != len(actual.gaps):
        mismatches.append(
            FieldMismatch("response_slots", "gap_count", len(view.gaps), len(actual.gaps))
        )
    gold_instruction, gold_body = _gold_phrases(view)
    moved = tuple(
        piece.gapped
        for instruction, group in ((True, gold_instruction), (False, gold_body))
        for piece in group
        if piece.has_gap
        and _located(actual, piece, instruction=instruction, gaps=False)
        and not _located(actual, piece, instruction=instruction, gaps=True)
    )
    if moved:
        mismatches.append(FieldMismatch("response_slots", "gap_position", moved, ()))
    for field in ("choices", "match_left", "match_right"):
        expected = tuple(words(entry) for entry in getattr(view, field))
        observed = tuple(words(entry) for entry in getattr(actual, field))
        if expected != observed:
            mismatches.append(FieldMismatch("response_slots", field, expected, observed))
    return mismatches
