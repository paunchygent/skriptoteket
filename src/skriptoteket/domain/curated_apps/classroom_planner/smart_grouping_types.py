"""Shared dataclasses for smart grouping.

Purpose:
    Keep smart-grouping result, config, and run-context types separate from
    the main solver flow so the search module can stay focused on orchestration.

Relationships:
    - consumed by `smart_grouping.py`
    - consumed by `smart_grouping_solver_support.py`
    - re-exported through `smart_grouping.py` for the current import surface
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    GroupAssignment,
    SeatAssignment,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import SeatTopology


@dataclass(frozen=True)
class LiveSeatingContinuityInput:
    """Represent one seating arrangement used for classroom-aware compactness."""

    room_context: SeatingRoomContextSnapshot
    seat_assignments: list[SeatAssignment]


@dataclass(frozen=True)
class ClassroomCompactnessConfig:
    """Define the tunable classroom-aware compactness weights for grouping."""

    elastic_radius: int = 2
    proximity_reward: float = 2.0
    distance_penalty: float = 3.0
    disconnected_component_penalty: float = 4.0
    singleton_component_penalty: float = 6.0
    nearest_component_penalty: float = 1.5
    split_block_penalty: float = 0.0
    secondary_block_penalty: float = 0.0
    secondary_zone_penalty: float = 0.0
    zone_row_gap_penalty: float = 0.0
    center_distance_penalty: float = 0.0


@dataclass(frozen=True)
class GreedySearchConfig:
    """Define optional extra greedy-search exploration for experiments."""

    randomized_order_attempts: int = 0
    random_seed: int = 0


@dataclass(frozen=True)
class SmartGroupingResult:
    """Return one scored smart-grouping candidate."""

    group_assignments: list[GroupAssignment]
    has_tradeoffs: bool


@dataclass(frozen=True)
class _CandidateScore:
    """Keep grouping precedence lexicographic across rule lanes."""

    explicit_rules: float
    classroom_compactness: float
    history: float
    size_balance: float
    diversity: float
    has_tradeoffs: bool

    @property
    def ordering_key(self) -> tuple[float, float, float, float, float]:
        """Return the solver comparison tuple in priority order."""

        return (
            self.explicit_rules,
            self.classroom_compactness,
            self.history,
            self.size_balance,
            self.diversity,
        )


@dataclass(frozen=True)
class _StaticScoringContext:
    """Hold the run-level grouping inputs shared by every candidate score."""

    keep_near_clusters: tuple[tuple[str, ...], ...]
    keep_apart_clusters: tuple[tuple[str, ...], ...]
    history_repeat_counts: dict[frozenset[str], int]
    current_partition_signature: tuple[tuple[str, ...], ...] | None
    seating_assignments_by_student: dict[str, str]
    topology: SeatTopology | None
    seat_pair_distances: dict[frozenset[str], int]
