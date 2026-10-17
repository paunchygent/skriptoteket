"""Derive native grid and rubric scores from the DOCX producer's stated points."""

from decimal import ROUND_FLOOR, Decimal

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import NativeExamCriterion


class InvalidTickValue(ValueError):
    """A printed total cannot represent a positive uniform native tick."""


def matching_score(points: int | float | None, ticks: int) -> tuple[Decimal, float, bool]:
    """One grid's uniform tick value, derived total and estimate flag (Q10, R11-R12).

    ``points`` is the total the answer key prints for the grid, or null when it prints
    none; ``ticks`` is the number of correct pairs. The tick value is the printed total
    per tick floored to 2 decimals, or the default 1 without a printed total. The derived
    total is tick × ticks with the same 2-decimal rounding, and the flag is true when the
    division was inexact or no total was printed. A tick below 0.01 is refused: no
    positive value can represent it.
    """
    if ticks < 1:
        raise ValueError("a matching grid needs at least one tick")
    if points is None:
        return Decimal(1), float(ticks), True
    stated = Decimal(str(points))
    tick = (stated / ticks).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
    if tick == 0:
        raise InvalidTickValue(
            f"points {points} cannot give a positive tick value over {ticks} ticks"
        )
    total = tick * ticks
    return tick, float(total), total != stated


def point_shares(total: int | float, count: int) -> tuple[int | float, ...]:
    """Even source-ordered shares, with the whole-point remainder first (D38)."""
    share, extra = divmod(total, count)
    return tuple(share + min(max(extra - rank, 0), 1) for rank in range(count))


def _whole_points(value: int | float) -> int | None:
    """The value as an int when it is a whole number, else None."""
    return int(value) if float(value).is_integer() else None


def free_text_criteria(
    produced: ProducedItem,
) -> tuple[tuple[NativeExamCriterion, ...], int | float | None, bool]:
    """The criteria the key states, the item's points and whether conversion estimated them.

    R14: a criterion the answer key states whole points for keeps them, and the item's
    points are their sum, or the item's own printed points when it prints them and they
    match. A guide without per-criterion points becomes one criterion at the item's whole
    printed points, or at 1 point when the item prints none, and counts as estimated. A
    fractional item point or criterion point, or a criteria sum that differs from the
    item's printed points, raises so admission keeps the question's source as its review
    item.
    """
    criteria = produced.criteria
    if not criteria:
        if produced.points is None:
            return (), None, False
        points = _whole_points(produced.points)
        if points is None:
            raise ValueError("free_text points are not whole")
        return (), points, False
    if any(criterion.points is None for criterion in criteria):
        if len(criteria) != 1:
            raise ValueError("a guide without per-criterion points is one criterion")
        (criterion,) = criteria
        points = 1 if produced.points is None else _whole_points(produced.points)
        if points is None or points < 1:
            raise ValueError("free_text points are not whole")
        return (NativeExamCriterion(text=criterion.text, points=points),), points, True
    whole_points: list[int] = []
    for criterion in criteria:
        if criterion.points is None:
            raise ValueError("free_text criterion points must be stated together")
        points = _whole_points(criterion.points)
        if points is None or points < 1:
            raise ValueError("free_text criterion points are not whole")
        whole_points.append(points)
    native = tuple(
        NativeExamCriterion(text=criterion.text, points=points)
        for criterion, points in zip(criteria, whole_points, strict=True)
    )
    total = sum(whole_points)
    if produced.points is None:
        return native, total, False
    stated = _whole_points(produced.points)
    if stated is None or stated != total:
        raise ValueError("free_text criteria sum does not match the item's stated points")
    return native, stated, False
