"""A10 spelling policy shared by offline evaluation and answer-key enrichment."""

from collections.abc import Collection

# A 1-3 character answer is a code, number or abbreviation: one changed letter makes a
# different answer, so it gets no extra spellings (user decision 2026-10-15).
MIN_SPELLING_VARIANT_ANSWER_LENGTH = 4
SHORT_ANSWER_MAX_LENGTH = 6
SHORT_ANSWER_MAX_DISTANCE = 1
LONG_ANSWER_MAX_DISTANCE = 2


def normalize_answer(text: str) -> str:
    return " ".join(text.split()).casefold()


def _damerau_levenshtein(left: str, right: str) -> int:
    """Unrestricted distance, including overlapping adjacent transpositions."""
    sentinel = len(left) + len(right)
    matrix = [[0] * (len(right) + 2) for _ in range(len(left) + 2)]
    matrix[0][0] = sentinel
    for i in range(len(left) + 1):
        matrix[i + 1][0] = sentinel
        matrix[i + 1][1] = i
    for j in range(len(right) + 1):
        matrix[0][j + 1] = sentinel
        matrix[1][j + 1] = j
    last_row: dict[str, int] = {}
    for i, a in enumerate(left, start=1):
        last_match_column = 0
        for j, b in enumerate(right, start=1):
            previous_row = last_row.get(b, 0)
            previous_column = last_match_column
            cost = 1
            if a == b:
                cost = 0
                last_match_column = j
            matrix[i + 1][j + 1] = min(
                matrix[i][j] + cost,
                matrix[i + 1][j] + 1,
                matrix[i][j + 1] + 1,
                matrix[previous_row][previous_column]
                + (i - previous_row - 1)
                + 1
                + (j - previous_column - 1),
            )
        last_row[a] = i
    return matrix[len(left) + 1][len(right) + 1]


def filter_answer_spelling_candidates(
    accepted_values: tuple[str, ...], candidates: tuple[str, ...]
) -> tuple[str, ...]:
    """Keep distinct, bounded spellings in producer order, at most three per answer."""
    answers = tuple(dict.fromkeys(normalize_answer(value) for value in accepted_values))
    counts = dict.fromkeys(answers, 0)
    seen = set(answers)
    kept: list[str] = []
    for candidate in candidates:
        normalized = normalize_answer(candidate)
        if not normalized or normalized in seen:
            continue
        for answer in answers:
            if counts[answer] < 3 and is_allowed_answer_spelling_variant(
                answer, candidate, other_gold_answers=answers
            ):
                kept.append(candidate.strip())
                seen.add(normalized)
                counts[answer] += 1
                break
    return tuple(kept)


def is_allowed_answer_spelling_variant(
    gold_answer: str, candidate: str, *, other_gold_answers: Collection[str] = ()
) -> bool:
    """Accept only a bounded extra spelling, excluding other item gold answers.

    Callers must separately require every original gold answer. Multi-word
    values use the distance and length of the entire normalised string.
    """
    gold = normalize_answer(gold_answer)
    variant = normalize_answer(candidate)
    if not gold or not variant or gold == variant:
        return False
    if len(gold) < MIN_SPELLING_VARIANT_ANSWER_LENGTH:
        return False
    if variant in {normalize_answer(value) for value in other_gold_answers}:
        return False
    bound = (
        SHORT_ANSWER_MAX_DISTANCE
        if len(gold) <= SHORT_ANSWER_MAX_LENGTH
        else LONG_ANSWER_MAX_DISTANCE
    )
    if abs(len(gold) - len(variant)) > bound:
        return False
    return _damerau_levenshtein(gold, variant) <= bound
