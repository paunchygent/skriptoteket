"""Focused smart-grouping precedence tests.

This module locks the classroom-aware compactness semantics for `ST-27-04`
without waiting for the full export-checkpoint and API slice to land.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
    NormalizedGroupingGroup,
    NormalizedGroupingSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    GroupAssignment,
    RelationshipKind,
    RelationshipRule,
    Roster,
    RosterSmartRules,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping import (
    ClassroomCompactnessConfig,
    LiveSeatingContinuityInput,
    _build_static_scoring_context,
    _improve_by_pair_swaps,
    _score_candidate,
    solve_smart_grouping,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping_scoring import (
    build_live_seating_topology,
    group_topology_cohesion,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import solve_smart_seating
from tests.unit.domain.curated_apps.classroom_planner import (
    smart_grouping_simulation_support as grouping_support,
)
from tests.unit.domain.curated_apps.classroom_planner import (
    smart_seating_solver_scenarios as g20_seating,
)
from tests.unit.domain.curated_apps.classroom_planner import (
    test_smart_grouping_solver_g20_sa24d as g20_grouping,
)
from tests.unit.domain.curated_apps.classroom_planner import (
    test_smart_seating_solver_bf25_g104 as bf25_seating,
)

_NOW = datetime(2026, 3, 29, tzinfo=timezone.utc)


def _roster() -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="SA24D",
        students=[
            Student(id="ada", display_name="Ada"),
            Student(id="alan", display_name="Alan"),
            Student(id="bea", display_name="Bea"),
            Student(id="cai", display_name="Cai"),
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _groups() -> list[DraftGroup]:
    return [
        DraftGroup(id="group-a", name="Grupp 1", sort_order=0, name_is_custom=False),
        DraftGroup(id="group-b", name="Grupp 2", sort_order=1, name_is_custom=False),
    ]


def _large_roster(student_count: int) -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="Large",
        students=[
            Student(id=f"student-{index}", display_name=f"Student {index}")
            for index in range(1, student_count + 1)
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _three_groups() -> list[DraftGroup]:
    return [
        DraftGroup(id="group-a", name="Grupp 1", sort_order=0, name_is_custom=False),
        DraftGroup(id="group-b", name="Grupp 2", sort_order=1, name_is_custom=False),
        DraftGroup(id="group-c", name="Grupp 3", sort_order=2, name_is_custom=False),
    ]


def _current_group_assignments() -> list[GroupAssignment]:
    return [
        GroupAssignment(student_id="ada", group_id="group-a"),
        GroupAssignment(student_id="alan", group_id="group-a"),
        GroupAssignment(student_id="bea", group_id="group-b"),
        GroupAssignment(student_id="cai", group_id="group-b"),
    ]


def _history_checkpoint(*, groups: list[list[str]]) -> GroupingExportCheckpoint:
    return GroupingExportCheckpoint(
        id=uuid4(),
        roster_id=uuid4(),
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        assignment_hash="checkpoint-hash",
        grouping_snapshot=NormalizedGroupingSnapshot(
            groups=[NormalizedGroupingGroup(student_ids=group) for group in groups],
            ungrouped_student_ids=[],
        ),
        created_at=_NOW,
    )


def _live_seating() -> LiveSeatingContinuityInput:
    return LiveSeatingContinuityInput(
        room_context=SeatingRoomContextSnapshot(
            grid_cols=2,
            grid_rows=2,
            seats=[
                {"id": "seat-1", "x": 0, "y": 0, "zone": None},
                {"id": "seat-2", "x": 1, "y": 0, "zone": None},
                {"id": "seat-3", "x": 0, "y": 1, "zone": None},
                {"id": "seat-4", "x": 1, "y": 1, "zone": None},
            ],
            fixtures=[],
        ),
        seat_assignments=[
            SeatAssignment(student_id="ada", seat_id="seat-1"),
            SeatAssignment(student_id="alan", seat_id="seat-2"),
            SeatAssignment(student_id="bea", seat_id="seat-3"),
            SeatAssignment(student_id="cai", seat_id="seat-4"),
        ],
    )


def _assignment_map(result) -> dict[str, str]:
    return {assignment.student_id: assignment.group_id for assignment in result.group_assignments}


def _table_bound_live_seating() -> LiveSeatingContinuityInput:
    template = bf25_seating._build_template()
    return LiveSeatingContinuityInput(
        room_context=bf25_seating._build_room_context(template),
        seat_assignments=[
            SeatAssignment(student_id="ada", seat_id="seat-1"),
            SeatAssignment(student_id="alan", seat_id="seat-2"),
            SeatAssignment(student_id="bea", seat_id="seat-8"),
            SeatAssignment(student_id="cai", seat_id="seat-7"),
            SeatAssignment(student_id="dex", seat_id="seat-13"),
            SeatAssignment(student_id="eve", seat_id="seat-14"),
        ],
    )


def test_keep_near_prefers_same_group_in_grouping() -> None:
    roster = _roster()
    result = solve_smart_grouping(
        roster=roster,
        groups=_groups(),
        smart_rules=RosterSmartRules(
            roster_id=roster.id,
            relationship_rules=[
                RelationshipRule(
                    id="near-1",
                    kind=RelationshipKind.KEEP_NEAR,
                    student_ids=["ada", "alan"],
                )
            ],
        ),
        current_group_assignments=[],
        history_checkpoints=[],
        live_seating_continuity=None,
    )

    assignments_by_student = _assignment_map(result)
    assert assignments_by_student["ada"] == assignments_by_student["alan"]


def test_grouping_history_penalizes_label_insensitive_pair_repeats() -> None:
    roster = _roster()
    result = solve_smart_grouping(
        roster=roster,
        groups=_groups(),
        smart_rules=RosterSmartRules(roster_id=roster.id),
        current_group_assignments=_current_group_assignments(),
        history_checkpoints=[
            _history_checkpoint(groups=[["ada", "alan"], ["bea", "cai"]]),
        ],
        live_seating_continuity=None,
    )

    assignments_by_student = _assignment_map(result)
    assert assignments_by_student["ada"] != assignments_by_student["alan"]
    assert assignments_by_student["bea"] != assignments_by_student["cai"]


def test_classroom_aware_compactness_outranks_rerun_diversity() -> None:
    roster = _roster()
    result = solve_smart_grouping(
        roster=roster,
        groups=_groups(),
        smart_rules=RosterSmartRules(roster_id=roster.id),
        current_group_assignments=_current_group_assignments(),
        history_checkpoints=[],
        live_seating_continuity=_live_seating(),
    )

    assignments_by_student = _assignment_map(result)
    seating = _live_seating()
    seat_coords_by_id = {seat.id: (seat.x, seat.y) for seat in seating.room_context.seats}
    seat_id_by_student = {
        assignment.student_id: assignment.seat_id for assignment in seating.seat_assignments
    }
    groups: dict[str, list[str]] = {}
    for student_id, group_id in assignments_by_student.items():
        groups.setdefault(group_id, []).append(student_id)

    assert sorted(len(student_ids) for student_ids in groups.values()) == [2, 2]
    for student_ids in groups.values():
        left_id, right_id = sorted(student_ids)
        left_x, left_y = seat_coords_by_id[seat_id_by_student[left_id]]
        right_x, right_y = seat_coords_by_id[seat_id_by_student[right_id]]
        assert abs(left_x - right_x) + abs(left_y - right_y) == 1


def test_explicit_rules_outrank_classroom_aware_compactness() -> None:
    roster = _roster()
    result = solve_smart_grouping(
        roster=roster,
        groups=_groups(),
        smart_rules=RosterSmartRules(
            roster_id=roster.id,
            relationship_rules=[
                RelationshipRule(
                    id="apart-1",
                    kind=RelationshipKind.KEEP_APART,
                    student_ids=["ada", "alan"],
                )
            ],
        ),
        current_group_assignments=_current_group_assignments(),
        history_checkpoints=[],
        live_seating_continuity=_live_seating(),
    )

    assignments_by_student = _assignment_map(result)
    assert assignments_by_student["ada"] != assignments_by_student["alan"]


def test_group_sizes_never_drift_beyond_plus_minus_one() -> None:
    roster = _large_roster(student_count=10)
    result = solve_smart_grouping(
        roster=roster,
        groups=_three_groups(),
        smart_rules=RosterSmartRules(roster_id=roster.id),
        current_group_assignments=[],
        history_checkpoints=[],
        live_seating_continuity=None,
    )

    group_sizes: dict[str, int] = {}
    for assignment in result.group_assignments:
        group_sizes[assignment.group_id] = group_sizes.get(assignment.group_id, 0) + 1

    assert max(group_sizes.values()) - min(group_sizes.values()) <= 1


def test_group_topology_cohesion_counts_split_singleton_islands() -> None:
    live_seating = _table_bound_live_seating()
    topology = build_live_seating_topology(room_context=live_seating.room_context)
    seat_assignments_by_student = {
        assignment.student_id: assignment.seat_id for assignment in live_seating.seat_assignments
    }

    cohesion = group_topology_cohesion(
        assignments_by_student={
            "ada": "group-a",
            "eve": "group-a",
            "alan": "group-b",
            "cai": "group-b",
            "bea": "group-b",
            "dex": "group-c",
        },
        seat_assignments_by_student=seat_assignments_by_student,
        topology=topology,
    )

    assert cohesion["group-a"].component_count == 2
    assert cohesion["group-a"].singleton_component_count == 2
    assert cohesion["group-a"].secondary_component_gap_sum > 0
    assert cohesion["group-b"].component_count == 1
    assert cohesion["group-c"].component_count == 1


def test_group_topology_cohesion_counts_zone_spill_and_row_gaps_for_bench_rooms() -> None:
    template = g20_seating.build_g20_template()
    topology = build_live_seating_topology(
        room_context=g20_seating.build_g20_room_context(template)
    )
    seats_by_zone: dict[int, list[str]] = {}
    for seat_id, zone_id in topology.local_zone_id_by_seat.items():
        seats_by_zone.setdefault(zone_id, []).append(seat_id)

    primary_zone_id = max(seats_by_zone, key=lambda zone_id: len(seats_by_zone[zone_id]))
    secondary_zone_id = min(seats_by_zone, key=lambda zone_id: len(seats_by_zone[zone_id]))
    primary_zone_seats = sorted(
        seats_by_zone[primary_zone_id],
        key=lambda seat_id: (
            topology.y_step_by_seat[seat_id],
            topology.x_step_by_seat[seat_id],
            seat_id,
        ),
    )
    secondary_zone_seats = sorted(
        seats_by_zone[secondary_zone_id],
        key=lambda seat_id: (
            topology.y_step_by_seat[seat_id],
            topology.x_step_by_seat[seat_id],
            seat_id,
        ),
    )
    top_primary = primary_zone_seats[0]
    bottom_primary = primary_zone_seats[-1]
    secondary_zone_seat = secondary_zone_seats[0]

    cohesion = group_topology_cohesion(
        assignments_by_student={
            "ada": "group-a",
            "alan": "group-a",
            "bea": "group-a",
        },
        seat_assignments_by_student={
            "ada": top_primary,
            "alan": bottom_primary,
            "bea": secondary_zone_seat,
        },
        topology=topology,
    )

    assert cohesion["group-a"].secondary_zone_student_count == 1
    assert cohesion["group-a"].primary_zone_row_gap_count >= 1


def test_pair_swap_improvement_recovers_better_g20_layout() -> None:
    roster = g20_seating.build_g20_roster()
    template = g20_seating.build_g20_template()
    reduced_keep_apart_cluster = (
        grouping_support.student_id("Petter Odehn"),
        grouping_support.student_id("Viktor Thornblad"),
        grouping_support.student_id("Leo Svartling"),
        grouping_support.student_id("Vincent Strandberg Gunnarsson"),
    )
    seating_rules = grouping_support.build_rules(
        roster_id=roster.id,
        keep_near_clusters=(g20_grouping._KEEP_NEAR_PAIR,),
        keep_apart_clusters=(reduced_keep_apart_cluster,),
        near_teacher_student_ids=tuple(sorted(g20_seating.NEAR_TEACHER_STUDENT_IDS)),
    )
    seating_result = solve_smart_seating(
        roster=roster,
        template=template,
        smart_rules=seating_rules,
        current_seat_assignments=[],
        history_checkpoints=g20_seating.build_g20_history_checkpoints(
            roster=roster,
            template=template,
        ),
    )
    live_seating = LiveSeatingContinuityInput(
        room_context=g20_seating.build_g20_room_context(template),
        seat_assignments=seating_result.seat_assignments,
    )
    grouping_rules = grouping_support.build_rules(
        roster_id=roster.id,
        keep_near_clusters=(g20_grouping._KEEP_NEAR_PAIR,),
        keep_apart_clusters=(reduced_keep_apart_cluster,),
    )
    static_context = _build_static_scoring_context(
        smart_rules=grouping_rules,
        current_group_assignments=[],
        history_checkpoints=[],
        live_seating_continuity=live_seating,
    )
    greedy_mapping = {
        "freja-essle": "group-1",
        "lily-sandahl": "group-1",
        "linnea-walfridson": "group-1",
        "viktor-thornblad": "group-1",
        "alva-andblad": "group-2",
        "edith-winlund-strandler": "group-2",
        "liam-vesterberg": "group-2",
        "alma-winald": "group-3",
        "julia-post": "group-3",
        "nora-schneider": "group-3",
        "vilma-ossner": "group-3",
        "ella-kjellman": "group-4",
        "hilda-grahn": "group-4",
        "kerstin-aitman": "group-4",
        "leo-svartling": "group-4",
        "ellen-odenman": "group-5",
        "molly-neijlind": "group-5",
        "sofia-andersson": "group-5",
        "vincent-strandberg-gunnarsson": "group-5",
        "agnes-leandersson": "group-6",
        "alexander-klemets": "group-6",
        "inger-isfeldt": "group-6",
        "lucas-kristiansson": "group-6",
        "julia-axelsson": "group-7",
        "moa-svensson": "group-7",
        "nellie-jonson": "group-7",
        "nora-johansson": "group-7",
        "elliot-antonsson": "group-8",
        "mary-parsons": "group-8",
        "otilia-olofsson-reijer": "group-8",
        "petter-odehn": "group-8",
    }
    config = ClassroomCompactnessConfig(
        elastic_radius=2,
        proximity_reward=2.0,
        distance_penalty=3.0,
        center_distance_penalty=2.0,
    )
    current_score = _score_candidate(
        assignments_by_student=greedy_mapping,
        group_ids=tuple(group.id for group in grouping_support.build_groups(group_count=8)),
        total_student_count=len(roster.students),
        static_context=static_context,
        classroom_compactness_config=config,
    )

    improved_mapping, improved_score = _improve_by_pair_swaps(
        assignments_by_student=greedy_mapping,
        current_score=current_score,
        group_ids=tuple(group.id for group in grouping_support.build_groups(group_count=8)),
        total_student_count=len(roster.students),
        static_context=static_context,
        classroom_compactness_config=config,
    )

    assert improved_score.ordering_key > current_score.ordering_key
    assert improved_mapping != greedy_mapping
