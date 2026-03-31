"""Topology helpers for smart-grouping compactness simulations.

Purpose:
    Keep visual-component and nearest-gap math out of the trial runner so the
    experiment analysis module stays below the repo line-budget limits.

Relationships:
    - consumed by `_smart_grouping_compactness_trials.py`
    - reuses `SeatTopology` from the classroom planner domain
"""

from __future__ import annotations

from collections import deque

from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import SeatTopology


def connected_student_components(
    *,
    student_ids: list[str],
    seating_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> list[list[str]]:
    """Return visual same-group seat components for one assigned group."""

    remaining = set(student_ids)
    same_group_student_ids = set(student_ids)
    components: list[list[str]] = []
    while remaining:
        seed = next(iter(remaining))
        queue = deque([seed])
        remaining.remove(seed)
        component: list[str] = []
        while queue:
            current = queue.popleft()
            component.append(current)
            neighbors = [
                candidate
                for candidate in list(remaining)
                if students_share_visual_component(
                    left_id=current,
                    right_id=candidate,
                    same_group_student_ids=same_group_student_ids,
                    seating_assignments_by_student=seating_assignments_by_student,
                    topology=topology,
                )
            ]
            for neighbor in neighbors:
                remaining.remove(neighbor)
                queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda component: (len(component), component))


def students_share_visual_component(
    *,
    left_id: str,
    right_id: str,
    same_group_student_ids: set[str],
    seating_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> bool:
    """Return whether two students belong to one occupied visual seat component."""

    pair = topology.pair(
        seating_assignments_by_student[left_id],
        seating_assignments_by_student[right_id],
    )
    if pair.same_block or pair.orthogonally_adjacent:
        return True
    if not pair.same_line_one_step:
        return False
    bridge_seat_id = bridge_seat_id_for_pair(
        left_seat_id=seating_assignments_by_student[left_id],
        right_seat_id=seating_assignments_by_student[right_id],
        topology=topology,
    )
    return bridge_seat_id is not None and any(
        seating_assignments_by_student[student_id] == bridge_seat_id
        for student_id in same_group_student_ids
    )


def nearest_component_gap(
    *,
    source_component: list[str],
    target_component: list[str],
    seating_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> int:
    """Return the nearest topology gap between two visual student components."""

    nearest_gap: int | None = None
    for source_student_id in source_component:
        for target_student_id in target_component:
            gap = topology.pair(
                seating_assignments_by_student[source_student_id],
                seating_assignments_by_student[target_student_id],
            ).grid_manhattan
            nearest_gap = gap if nearest_gap is None else min(nearest_gap, gap)
    return 0 if nearest_gap is None else nearest_gap


def bridge_seat_id_for_pair(
    *,
    left_seat_id: str,
    right_seat_id: str,
    topology: SeatTopology,
) -> str | None:
    """Return the occupied bridge seat id for one same-line one-step pair, if any."""

    left_x = topology.x_step_by_seat[left_seat_id]
    right_x = topology.x_step_by_seat[right_seat_id]
    left_y = topology.y_step_by_seat[left_seat_id]
    right_y = topology.y_step_by_seat[right_seat_id]
    if left_x == right_x and abs(left_y - right_y) == 2:
        target = (left_x, (left_y + right_y) // 2)
    elif left_y == right_y and abs(left_x - right_x) == 2:
        target = ((left_x + right_x) // 2, left_y)
    else:
        return None
    for seat_id, seat_x in topology.x_step_by_seat.items():
        if seat_x == target[0] and topology.y_step_by_seat[seat_id] == target[1]:
            return seat_id
    return None
