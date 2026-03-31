"""Scoring helpers for smart grouping.

Purpose:
    Keep label-insensitive grouping-history math and classroom-aware
    seat-topology distance extraction separate from the main smart-grouping
    search module.

Relationships:
    - consumed by `smart_grouping.py`
    - shared by future grouping-history persistence and smart-grouping tests
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import inf

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import RoomFixture, Seat
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)


@dataclass(frozen=True)
class GroupTopologyCohesion:
    """Capture topology-aware anti-island metrics for one assigned group."""

    component_count: int
    singleton_component_count: int
    secondary_component_gap_sum: int
    secondary_component_gap_cost: int
    block_count: int
    secondary_block_student_count: int
    secondary_block_student_cost: int
    secondary_zone_student_count: int
    secondary_zone_student_cost: int
    primary_zone_row_gap_count: int
    primary_zone_row_gap_cost: int


def history_coassignment_counts(
    history_checkpoints: list[GroupingExportCheckpoint],
) -> dict[frozenset[str], int]:
    """Count how often each student pair has appeared in the same history group."""

    pair_counts: dict[frozenset[str], int] = defaultdict(int)
    for checkpoint in history_checkpoints:
        for group in checkpoint.grouping_snapshot.groups:
            for left_id, right_id in combinations(sorted(group.student_ids), 2):
                pair_counts[frozenset({left_id, right_id})] += 1
    return dict(pair_counts)


def build_live_seating_topology(*, room_context: SeatingRoomContextSnapshot) -> SeatTopology:
    """Build one topology object from the current live seating room context."""

    seats = [Seat(id=seat.id, x=seat.x, y=seat.y, zone=seat.zone) for seat in room_context.seats]
    fixtures = [
        RoomFixture(
            id=fixture.id,
            type=fixture.type,
            x=fixture.x,
            y=fixture.y,
            width=fixture.width,
            height=fixture.height,
            label=fixture.label,
        )
        for fixture in room_context.fixtures
    ]
    return build_seat_topology(
        seats=seats,
        anchor=infer_teaching_anchor(room_context=room_context),
        fixtures=fixtures,
    )


def seat_topology_pair_distances(
    *,
    topology: SeatTopology,
    seat_assignments_by_student: dict[str, str],
) -> dict[frozenset[str], int]:
    """Return pairwise graph distances for the current topology context."""

    graph = _distance_graph(topology=topology)
    pair_distances: dict[frozenset[str], int] = {}
    for left_id, right_id in combinations(sorted(seat_assignments_by_student), 2):
        left_seat_id = seat_assignments_by_student[left_id]
        right_seat_id = seat_assignments_by_student[right_id]
        step_distance = _shortest_path_distance(
            graph=graph,
            start_seat_id=left_seat_id,
            goal_seat_id=right_seat_id,
        )
        if step_distance is None:
            step_distance = topology.pair(left_seat_id, right_seat_id).grid_manhattan
        pair_distances[frozenset({left_id, right_id})] = step_distance
    return pair_distances


def group_topology_cohesion(
    *,
    assignments_by_student: dict[str, str],
    seat_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> dict[str, GroupTopologyCohesion]:
    """Describe how fragmented each same-group seat region is on the topology graph."""

    distance_graph = _distance_graph(topology=topology)
    students_by_group: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        if student_id not in seat_assignments_by_student:
            continue
        students_by_group[group_id].append(student_id)

    cohesion_by_group: dict[str, GroupTopologyCohesion] = {}
    for group_id, student_ids in students_by_group.items():
        seat_ids = [seat_assignments_by_student[student_id] for student_id in sorted(student_ids)]
        components = _connected_components(
            node_ids=seat_ids,
            graph=_occupied_group_graph(node_ids=seat_ids, topology=topology),
        )
        ordered_components = sorted(components, key=lambda component: (-len(component), component))
        secondary_gap_sum = 0
        secondary_gap_cost = 0
        if ordered_components:
            primary_component = ordered_components[0]
            for component in ordered_components[1:]:
                gap = _nearest_component_gap(
                    source_component=component,
                    target_component=primary_component,
                    graph=distance_graph,
                    topology=topology,
                )
                secondary_gap_sum += gap
                secondary_gap_cost += gap**2
        singleton_component_count = sum(
            1 for component in ordered_components if len(component) == 1 and len(student_ids) > 1
        )
        block_counts: dict[int, int] = defaultdict(int)
        for seat_id in seat_ids:
            block_counts[topology.block_id_by_seat[seat_id]] += 1
        primary_block_size = max(block_counts.values(), default=0)
        secondary_block_student_count = max(len(seat_ids) - primary_block_size, 0)
        zone_counts: dict[int, int] = defaultdict(int)
        row_steps_by_zone: dict[int, set[int]] = defaultdict(set)
        for seat_id in seat_ids:
            zone_id = topology.local_zone_id_by_seat[seat_id]
            zone_counts[zone_id] += 1
            row_steps_by_zone[zone_id].add(topology.y_step_by_seat[seat_id])
        primary_zone_id = min(
            zone_counts,
            key=lambda zone_id: (-zone_counts[zone_id], zone_id),
            default=0,
        )
        primary_zone_size = zone_counts.get(primary_zone_id, 0)
        secondary_zone_student_count = max(len(seat_ids) - primary_zone_size, 0)
        primary_zone_rows = sorted(row_steps_by_zone.get(primary_zone_id, set()))
        primary_zone_row_gap_count = 0
        if primary_zone_rows:
            primary_zone_row_gap_count = (
                primary_zone_rows[-1] - primary_zone_rows[0] + 1 - len(primary_zone_rows)
            )
        cohesion_by_group[group_id] = GroupTopologyCohesion(
            component_count=len(ordered_components),
            singleton_component_count=singleton_component_count,
            secondary_component_gap_sum=secondary_gap_sum,
            secondary_component_gap_cost=secondary_gap_cost,
            block_count=len(block_counts),
            secondary_block_student_count=secondary_block_student_count,
            secondary_block_student_cost=secondary_block_student_count**2,
            secondary_zone_student_count=secondary_zone_student_count,
            secondary_zone_student_cost=secondary_zone_student_count**2,
            primary_zone_row_gap_count=primary_zone_row_gap_count,
            primary_zone_row_gap_cost=primary_zone_row_gap_count**2,
        )
    return cohesion_by_group


def group_center_distance_cost(
    *,
    assignments_by_student: dict[str, str],
    seat_assignments_by_student: dict[str, str],
    pair_distances: dict[frozenset[str], int],
    elastic_radius: int,
) -> float:
    """Return one medoid-based squared overflow cost across all assigned groups."""

    students_by_group: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        if student_id not in seat_assignments_by_student:
            continue
        students_by_group[group_id].append(student_id)

    total_cost = 0.0
    for student_ids in students_by_group.values():
        if len(student_ids) <= 1:
            continue
        ordered_students = sorted(student_ids)
        center_student_id = min(
            ordered_students,
            key=lambda candidate_id: (
                _center_candidate_cost(
                    candidate_id=candidate_id,
                    student_ids=ordered_students,
                    pair_distances=pair_distances,
                    elastic_radius=elastic_radius,
                ),
                candidate_id,
            ),
        )
        total_cost += _center_candidate_cost(
            candidate_id=center_student_id,
            student_ids=ordered_students,
            pair_distances=pair_distances,
            elastic_radius=elastic_radius,
        )
    return total_cost


def normalized_partition_signature(
    assignments_by_student: dict[str, str],
) -> tuple[tuple[str, ...], ...]:
    """Return one label-insensitive partition signature for repeat detection."""

    groups: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        groups[group_id].append(student_id)
    normalized_groups = [tuple(sorted(student_ids)) for student_ids in groups.values()]
    return tuple(sorted(normalized_groups, key=lambda group: (len(group), group)))


def normalized_size_deviation(
    *,
    assignments_by_student: dict[str, str],
    group_ids: tuple[str, ...],
) -> float:
    """Return the total deviation from the most even feasible group distribution."""

    counts = {group_id: 0 for group_id in group_ids}
    for group_id in assignments_by_student.values():
        counts[group_id] += 1
    student_count = len(assignments_by_student)
    group_count = len(group_ids)
    if group_count <= 0:
        return inf
    lower = student_count // group_count
    upper = lower + (1 if student_count % group_count else 0)
    return float(sum(min(abs(count - lower), abs(count - upper)) for count in counts.values()))


def _distance_graph(*, topology: SeatTopology) -> dict[str, tuple[str, ...]]:
    seat_ids = sorted(topology.seats_by_id)
    graph: dict[str, list[str]] = {seat_id: [] for seat_id in seat_ids}
    for index, left_seat_id in enumerate(seat_ids):
        for right_seat_id in seat_ids[index + 1 :]:
            pair = topology.pair(left_seat_id, right_seat_id)
            if not pair.same_block and not pair.orthogonally_adjacent:
                continue
            graph[left_seat_id].append(right_seat_id)
            graph[right_seat_id].append(left_seat_id)
    return {seat_id: tuple(sorted(neighbors)) for seat_id, neighbors in graph.items()}


def _occupied_group_graph(
    *,
    node_ids: list[str],
    topology: SeatTopology,
) -> dict[str, tuple[str, ...]]:
    """Build one stricter same-group connectivity graph for cohesion checks."""

    node_set = set(node_ids)
    graph: dict[str, list[str]] = {seat_id: [] for seat_id in node_ids}
    ordered_nodes = sorted(node_ids)
    for index, left_seat_id in enumerate(ordered_nodes):
        for right_seat_id in ordered_nodes[index + 1 :]:
            pair = topology.pair(left_seat_id, right_seat_id)
            if pair.same_block or pair.orthogonally_adjacent:
                graph[left_seat_id].append(right_seat_id)
                graph[right_seat_id].append(left_seat_id)
                continue
            if not pair.same_line_one_step:
                continue
            bridge_seat_id = _bridge_seat_id(
                left_seat_id=left_seat_id,
                right_seat_id=right_seat_id,
                topology=topology,
            )
            if bridge_seat_id is None or bridge_seat_id not in node_set:
                continue
            graph[left_seat_id].append(right_seat_id)
            graph[right_seat_id].append(left_seat_id)
    return {seat_id: tuple(sorted(neighbors)) for seat_id, neighbors in graph.items()}


def _shortest_path_distance(
    *,
    graph: dict[str, tuple[str, ...]],
    start_seat_id: str,
    goal_seat_id: str,
) -> int | None:
    if start_seat_id == goal_seat_id:
        return 0
    if start_seat_id not in graph or goal_seat_id not in graph:
        return None

    frontier: list[tuple[str, int]] = [(start_seat_id, 0)]
    visited = {start_seat_id}
    while frontier:
        current_seat_id, distance = frontier.pop(0)
        for neighbor_id in graph[current_seat_id]:
            if neighbor_id == goal_seat_id:
                return distance + 1
            if neighbor_id in visited:
                continue
            visited.add(neighbor_id)
            frontier.append((neighbor_id, distance + 1))
    return None


def _connected_components(
    *,
    node_ids: list[str],
    graph: dict[str, tuple[str, ...]],
) -> list[list[str]]:
    remaining = set(node_ids)
    components: list[list[str]] = []
    while remaining:
        seed = next(iter(remaining))
        queue = [seed]
        remaining.remove(seed)
        component: list[str] = []
        while queue:
            current = queue.pop(0)
            component.append(current)
            for neighbor in graph.get(current, ()):
                if neighbor not in remaining:
                    continue
                remaining.remove(neighbor)
                queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda component: (len(component), component))


def _nearest_component_gap(
    *,
    source_component: list[str],
    target_component: list[str],
    graph: dict[str, tuple[str, ...]],
    topology: SeatTopology,
) -> int:
    nearest = inf
    for source_seat_id in source_component:
        for target_seat_id in target_component:
            distance = _shortest_path_distance(
                graph=graph,
                start_seat_id=source_seat_id,
                goal_seat_id=target_seat_id,
            )
            if distance is None:
                distance = topology.pair(source_seat_id, target_seat_id).grid_manhattan
            nearest = min(nearest, distance)
    return 0 if nearest is inf else int(nearest)


def _center_candidate_cost(
    *,
    candidate_id: str,
    student_ids: list[str],
    pair_distances: dict[frozenset[str], int],
    elastic_radius: int,
) -> float:
    total_cost = 0.0
    for student_id in student_ids:
        if student_id == candidate_id:
            continue
        pair_key = frozenset({candidate_id, student_id})
        distance = pair_distances.get(pair_key)
        if distance is None:
            continue
        overflow = max(distance - elastic_radius, 0)
        total_cost += float(overflow**2)
    return total_cost


def _bridge_seat_id(
    *,
    left_seat_id: str,
    right_seat_id: str,
    topology: SeatTopology,
) -> str | None:
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
        if seat_x != target[0]:
            continue
        if topology.y_step_by_seat[seat_id] != target[1]:
            continue
        return seat_id
    return None
