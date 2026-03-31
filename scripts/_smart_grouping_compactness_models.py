"""Shared dataclasses for smart-grouping compactness simulations.

Purpose:
    Keep simulation scenario and report types separate from the support,
    analysis, and rendering helpers so each experiment module stays focused.

Relationships:
    - consumed by `_smart_grouping_compactness_support.py`
    - consumed by `_smart_grouping_compactness_trials.py`
    - consumed by `_smart_grouping_compactness_rendering.py`
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    RoomTemplate,
    Roster,
    RosterSmartRules,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import SeatTopology
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping import (
    ClassroomCompactnessConfig,
)


@dataclass(frozen=True)
class CandidateSpec:
    """Describe one compactness candidate to compare in the simulation."""

    key: str
    label: str
    compactness_config: ClassroomCompactnessConfig | None
    trial_count: int
    randomized_order_attempts: int


@dataclass(frozen=True)
class ScenarioDefinition:
    """Hold one canonical classroom scenario with a full seating projection."""

    key: str
    label: str
    roster: Roster
    template: RoomTemplate
    topology: SeatTopology
    groups: list[DraftGroup]
    grouping_rules: RosterSmartRules
    keep_near_pair: tuple[str, str] | None
    keep_apart_cluster: tuple[str, ...] | None
    seating_assignments_by_student: dict[str, str]


@dataclass(frozen=True)
class CandidateReport:
    """Capture one candidate result plus the derived overlay metrics."""

    key: str
    label: str
    trial_count: int
    randomized_order_attempts: int
    best_trial_index: int
    best_random_seed: int
    used_classroom_compactness: bool
    compactness_config: dict[str, float | int] | None
    rule_valid_rate: float
    keep_near_valid_rate: float | None
    keep_apart_valid_rate: float | None
    zero_fragmentation_rate: float
    zero_singleton_rate: float
    zero_split_block_rate: float
    zero_zone_spill_rate: float
    zero_zone_gap_rate: float
    assignments_by_student: dict[str, str]
    keep_near_valid: bool | None
    keep_apart_valid: bool | None
    mean_within_group_distance: float
    max_within_group_distance: int
    fragmented_group_count: int
    total_group_component_count: int
    singleton_component_count: int
    secondary_component_gap_sum: int
    split_block_group_count: int
    secondary_block_student_count: int
    secondary_zone_student_count: int
    primary_zone_row_gap_count: int
    component_student_ids_by_group: dict[str, list[list[str]]]
    artifact_path: str


@dataclass(frozen=True)
class TrialReport:
    """Capture one single simulation trial before aggregation."""

    trial_index: int
    random_seed: int
    assignments_by_student: dict[str, str]
    keep_near_valid: bool | None
    keep_apart_valid: bool | None
    mean_within_group_distance: float
    max_within_group_distance: int
    fragmented_group_count: int
    total_group_component_count: int
    singleton_component_count: int
    secondary_component_gap_sum: int
    split_block_group_count: int
    secondary_block_student_count: int
    secondary_zone_student_count: int
    primary_zone_row_gap_count: int
    component_student_ids_by_group: dict[str, list[list[str]]]
