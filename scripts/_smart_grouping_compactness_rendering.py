"""Rendering helpers for smart-grouping compactness overlays.

Purpose:
    Generate rough PNG seating overlays for compactness experiments without
    mixing drawing code into scenario assembly or trial analysis.

Relationships:
    - consumed by `_smart_grouping_compactness_support.py`
    - uses scenario/report dataclasses from `_smart_grouping_compactness_models.py`
"""

from __future__ import annotations

from pathlib import Path

from reportlab.graphics import renderPM
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors

from scripts._smart_grouping_compactness_models import CandidateReport, ScenarioDefinition
from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate

_CELL_SIZE = 34
_BASE_GAP = 16
_OUTER_MARGIN = 52
_LEGEND_WIDTH = 340
_TITLE_HEIGHT = 120
_TEXT_COLOR = colors.HexColor("#243554")
_GRID_COLOR = colors.HexColor("#C9D3E1")
_COMPONENT_FILL = colors.Color(1.0, 1.0, 1.0, alpha=0.0)
_PALETTE = (
    colors.HexColor("#294A78"),
    colors.HexColor("#A44343"),
    colors.HexColor("#3E6E54"),
    colors.HexColor("#8A5B24"),
    colors.HexColor("#77508B"),
    colors.HexColor("#2F6F8A"),
    colors.HexColor("#AA6C39"),
    colors.HexColor("#4B5A7C"),
)


def render_seating_projection(
    *,
    scenario: ScenarioDefinition,
    candidate_report: CandidateReport,
    output_path: Path,
) -> None:
    """Render one rough PNG overlay for the grouping candidate."""

    x_pos_by_value, y_pos_by_value = _visual_axis_positions(template=scenario.template)
    max_x = max(x_pos_by_value.values(), default=0)
    max_y = max(y_pos_by_value.values(), default=0)
    width = _OUTER_MARGIN * 2 + max_x + _CELL_SIZE + _LEGEND_WIDTH
    height = _OUTER_MARGIN * 2 + _TITLE_HEIGHT + max_y + _CELL_SIZE + 30
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, fillColor=colors.white, strokeColor=colors.white))

    title_y = height - 48
    drawing.add(
        String(
            _OUTER_MARGIN,
            title_y,
            f"{scenario.label} · {candidate_report.label}",
            fontName="Helvetica-Bold",
            fontSize=18,
            fillColor=_TEXT_COLOR,
        )
    )
    drawing.add(
        String(
            _OUTER_MARGIN,
            title_y - 22,
            _metric_line(candidate_report),
            fontName="Helvetica",
            fontSize=10,
            fillColor=_TEXT_COLOR,
        )
    )
    drawing.add(
        String(
            _OUTER_MARGIN,
            title_y - 40,
            _rate_line(candidate_report),
            fontName="Helvetica",
            fontSize=10,
            fillColor=_TEXT_COLOR,
        )
    )

    seat_origin_y = height - _OUTER_MARGIN - _TITLE_HEIGHT
    group_color_by_id = {
        group.id: _PALETTE[index % len(_PALETTE)] for index, group in enumerate(scenario.groups)
    }
    student_by_id = {student.id: student for student in scenario.roster.students}

    for seat in scenario.template.seats:
        x = _OUTER_MARGIN + x_pos_by_value[seat.x]
        y = seat_origin_y - y_pos_by_value[seat.y]
        drawing.add(
            Rect(
                x,
                y,
                _CELL_SIZE,
                _CELL_SIZE,
                fillColor=colors.white,
                strokeColor=_GRID_COLOR,
                strokeWidth=1.0,
                rx=2,
                ry=2,
            )
        )

    component_boxes = _component_boxes(
        scenario=scenario,
        candidate_report=candidate_report,
        x_pos_by_value=x_pos_by_value,
        y_pos_by_value=y_pos_by_value,
        seat_origin_y=seat_origin_y,
    )
    for group_id, boxes in component_boxes.items():
        stroke = group_color_by_id[group_id]
        for left, bottom, right, top in boxes:
            drawing.add(
                Rect(
                    left - 6,
                    bottom - 6,
                    (right - left) + _CELL_SIZE + 12,
                    (top - bottom) + _CELL_SIZE + 12,
                    fillColor=_COMPONENT_FILL,
                    strokeColor=stroke,
                    strokeWidth=2.0,
                )
            )

    for student_id, group_id in candidate_report.assignments_by_student.items():
        seat = next(
            seat
            for seat in scenario.template.seats
            if seat.id == scenario.seating_assignments_by_student[student_id]
        )
        x = _OUTER_MARGIN + x_pos_by_value[seat.x]
        y = seat_origin_y - y_pos_by_value[seat.y]
        fill = group_color_by_id[group_id]
        drawing.add(
            Rect(
                x + 2,
                y + 2,
                _CELL_SIZE - 4,
                _CELL_SIZE - 4,
                fillColor=fill,
                strokeColor=fill,
                strokeWidth=1.0,
                rx=2,
                ry=2,
            )
        )
        drawing.add(
            String(
                x + 6,
                y + 12,
                _student_initials(student_by_id[student_id].display_name),
                fontName="Helvetica-Bold",
                fontSize=9,
                fillColor=colors.white,
            )
        )

    legend_x = _OUTER_MARGIN + max_x + _CELL_SIZE + 44
    legend_y = height - _OUTER_MARGIN - 24
    drawing.add(
        String(
            legend_x,
            legend_y,
            "Grupper och komponenter",
            fontName="Helvetica-Bold",
            fontSize=12,
            fillColor=_TEXT_COLOR,
        )
    )
    legend_cursor_y = legend_y - 28
    for group in scenario.groups:
        components = candidate_report.component_student_ids_by_group.get(group.id, [])
        drawing.add(
            Rect(
                legend_x,
                legend_cursor_y - 10,
                18,
                18,
                fillColor=group_color_by_id[group.id],
                strokeColor=group_color_by_id[group.id],
                strokeWidth=1.0,
            )
        )
        drawing.add(
            String(
                legend_x + 28,
                legend_cursor_y - 1,
                f"{group.name}: {sum(len(component) for component in components)} elever, "
                f"{len(components)} delytor",
                fontName="Helvetica",
                fontSize=10,
                fillColor=_TEXT_COLOR,
            )
        )
        legend_cursor_y -= 24

    output_path.parent.mkdir(parents=True, exist_ok=True)
    renderPM.drawToFile(drawing, str(output_path), fmt="PNG")


def _component_boxes(
    *,
    scenario: ScenarioDefinition,
    candidate_report: CandidateReport,
    x_pos_by_value: dict[int, int],
    y_pos_by_value: dict[int, int],
    seat_origin_y: int,
) -> dict[str, list[tuple[int, int, int, int]]]:
    seat_by_id = {seat.id: seat for seat in scenario.template.seats}
    boxes: dict[str, list[tuple[int, int, int, int]]] = {}
    for group_id, components in candidate_report.component_student_ids_by_group.items():
        boxes[group_id] = []
        for component in components:
            seats = [
                seat_by_id[scenario.seating_assignments_by_student[student_id]]
                for student_id in component
            ]
            left = min(_OUTER_MARGIN + x_pos_by_value[seat.x] for seat in seats)
            right = max(_OUTER_MARGIN + x_pos_by_value[seat.x] for seat in seats)
            top = max(seat_origin_y - y_pos_by_value[seat.y] for seat in seats)
            bottom = min(seat_origin_y - y_pos_by_value[seat.y] for seat in seats)
            boxes[group_id].append((left, bottom, right, top))
    return boxes


def _visual_axis_positions(*, template: RoomTemplate) -> tuple[dict[int, int], dict[int, int]]:
    return (
        _axis_visual_positions([seat.x for seat in template.seats]),
        _axis_visual_positions([seat.y for seat in template.seats]),
    )


def _axis_visual_positions(values: list[int]) -> dict[int, int]:
    ordered = sorted(set(values))
    if not ordered:
        return {}
    diffs = [
        right - left for left, right in zip(ordered, ordered[1:], strict=False) if right > left
    ]
    min_diff = min(diffs, default=1)
    positions = {ordered[0]: 0}
    cursor = 0
    for previous, current in zip(ordered, ordered[1:], strict=False):
        gap_units = max(round((current - previous) / min_diff), 1)
        cursor += _CELL_SIZE + (_BASE_GAP * gap_units)
        positions[current] = cursor
    return positions


def _student_initials(display_name: str) -> str:
    parts = [part for part in display_name.split() if part]
    if not parts:
        return "?"
    return "".join(part[0].upper() for part in parts[:2])


def _metric_line(candidate_report: CandidateReport) -> str:
    keep_near = (
        "-"
        if candidate_report.keep_near_valid is None
        else "ok"
        if candidate_report.keep_near_valid
        else "brott"
    )
    keep_apart = (
        "-"
        if candidate_report.keep_apart_valid is None
        else "ok"
        if candidate_report.keep_apart_valid
        else "brott"
    )
    return (
        f"Keep near: {keep_near} · Keep apart: {keep_apart} · "
        f"medeldistans {candidate_report.mean_within_group_distance:.2f} · "
        f"maxdistans {candidate_report.max_within_group_distance} · "
        f"fragmenterade grupper {candidate_report.fragmented_group_count} · "
        f"singelöar {candidate_report.singleton_component_count} · "
        f"sekundär gap-summa {candidate_report.secondary_component_gap_sum} · "
        f"splittrade blockgrupper {candidate_report.split_block_group_count} · "
        f"zonspill {candidate_report.secondary_zone_student_count} · "
        f"radglapp {candidate_report.primary_zone_row_gap_count}"
    )


def _rate_line(candidate_report: CandidateReport) -> str:
    parts = [
        f"regelträff {candidate_report.rule_valid_rate:.2f}",
        f"fragmentfri {candidate_report.zero_fragmentation_rate:.2f}",
        f"singelfri {candidate_report.zero_singleton_rate:.2f}",
        f"blockfri {candidate_report.zero_split_block_rate:.2f}",
        f"zonfri {candidate_report.zero_zone_spill_rate:.2f}",
        f"radtät {candidate_report.zero_zone_gap_rate:.2f}",
        (
            f"bästa försök {candidate_report.best_trial_index + 1}/{candidate_report.trial_count}"
            f" (seed {candidate_report.best_random_seed})"
        ),
    ]
    return " · ".join(parts)
