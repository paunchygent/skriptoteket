"""Grouping: shuffle students into groups that minimise repeated pairs."""

from __future__ import annotations

import random

from .roster import dedupe_names

MAX_SHUFFLES = 200


def pairs_for_groups(groups: list[list[str]]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for group in groups:
        cleaned = dedupe_names(group)
        for idx, name in enumerate(cleaned):
            for other in cleaned[idx + 1 :]:
                a, b = sorted((name.casefold(), other.casefold()))
                pairs.add((a, b))
    return pairs


def _score_groups(groups: list[list[str]], previous_pairs: set[tuple[str, str]]) -> int:
    if not previous_pairs:
        return 0
    score = 0
    for group in groups:
        cleaned = dedupe_names(group)
        for idx, name in enumerate(cleaned):
            for other in cleaned[idx + 1 :]:
                a, b = sorted((name.casefold(), other.casefold()))
                if (a, b) in previous_pairs:
                    score += 1
    return score


def _chunk_groups(students: list[str], group_size: int) -> list[list[str]]:
    return [students[i : i + group_size] for i in range(0, len(students), group_size)]


def build_groups(
    students: list[str],
    group_size: int,
    previous_pairs: set[tuple[str, str]],
) -> tuple[list[list[str]], int]:
    if not students:
        return ([], 0)
    rng = random.Random()
    best_groups: list[list[str]] = []
    best_score = float("inf")
    attempts = MAX_SHUFFLES if previous_pairs else 1
    pool = students[:]

    for _ in range(attempts):
        rng.shuffle(pool)
        groups = _chunk_groups(pool, group_size)
        score = _score_groups(groups, previous_pairs)
        if score < best_score:
            best_score = float(score)
            best_groups = [group[:] for group in groups]
            if score == 0:
                break
    return (best_groups, int(best_score if best_score != float("inf") else 0))
