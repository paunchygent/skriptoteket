"""The saved print order of an ordering question (TASK-SKRIPT-39-06-08 D1, D2, D5, D6).

Purpose:
    An ordering question's steps are its choices; their list order is the answer key (D1).
    Every print shows the steps in one saved shuffled order (D2, D5), and with two or more
    steps that order never equals the key order (D6). This module draws that order and
    checks it against the steps.

Relationships:
    Used by ``native_exam_item`` for the shape rule and by ``native_exam_change_type`` when
    a question becomes an ordering question. The workspace draws the same way in
    ``examWorkspaceOrdering.ts`` for "Blanda om".
"""

from __future__ import annotations

import random
from collections.abc import Sequence


def draw_print_order(step_ids: Sequence[str], rng: random.Random) -> tuple[str, ...]:
    """A shuffled order of the steps that is never the key order once there are two."""
    order = list(step_ids)
    if len(order) < 2:
        return tuple(order)
    rng.shuffle(order)
    if order == list(step_ids):
        # A rotation by 1..n-1 of distinct ids never equals the key order.
        shift = rng.randrange(1, len(order))
        order = order[shift:] + order[:shift]
    return tuple(order)


def validate_print_order(step_ids: Sequence[str], print_order: Sequence[str]) -> None:
    """The print order holds every step once and, from two steps, is not the key order."""
    if sorted(print_order) != sorted(step_ids):
        raise ValueError("ordering print order must hold every step exactly once")
    if len(step_ids) >= 2 and tuple(print_order) == tuple(step_ids):
        raise ValueError("ordering print order must differ from the answer-key order")
