"""History diversity summaries for Klassrumskartan smart seating.

Purpose:
    Convert accepted seating checkpoints into compact anti-repeat signals for
    the smart seating solver.

Relationships:
    - Consumes export-backed checkpoint snapshots from the classroom-planner
      domain contract.
    - Provides pure scoring summaries used by the smart-seating candidate
      scorer without reaching into persistence or application handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import TypeVar

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RoomFixture,
    Seat,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    KeepNearRelationMode,
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)

LayoutSignature = tuple[tuple[str, str], ...]
PlacementCountsByStudent = dict[str, dict[str, int]]
RankCountsByStudent = dict[str, dict[int, int]]

_Key = TypeVar("_Key")
_OuterKey = TypeVar("_OuterKey")
_InnerKey = TypeVar("_InnerKey")


@dataclass(frozen=True)
class SeatingHistoryDiversity:
    """Carry checkpoint-backed repetition counts for seating diversity scoring."""

    layout_counts: dict[LayoutSignature, int]
    seat_counts_by_student: PlacementCountsByStudent
    block_counts_by_student: RankCountsByStudent
    zone_counts_by_student: RankCountsByStudent
    front_rank_counts_by_student: RankCountsByStudent
    keep_near_pair_seat_counts: dict[frozenset[str], dict[frozenset[str], int]]
    keep_near_pair_mode_counts: dict[frozenset[str], dict[KeepNearRelationMode, int]]
    keep_apart_pair_seat_counts: dict[frozenset[str], dict[frozenset[str], int]]
    keep_apart_block_signature_counts: dict[frozenset[str], dict[tuple[int, ...], int]]
    keep_apart_zone_signature_counts: dict[frozenset[str], dict[tuple[int, ...], int]]

    @property
    def has_checkpoints(self) -> bool:
        """Return whether any accepted checkpoint contributed repetition data."""

        return bool(self.layout_counts)


def empty_seating_history_diversity() -> SeatingHistoryDiversity:
    """Return an empty history summary for no-history smart runs."""

    return SeatingHistoryDiversity(
        layout_counts={},
        seat_counts_by_student={},
        block_counts_by_student={},
        zone_counts_by_student={},
        front_rank_counts_by_student={},
        keep_near_pair_seat_counts={},
        keep_near_pair_mode_counts={},
        keep_apart_pair_seat_counts={},
        keep_apart_block_signature_counts={},
        keep_apart_zone_signature_counts={},
    )


def build_seating_history_diversity(
    *,
    history_checkpoints: list[SeatingExportCheckpoint],
    keep_near_clusters: list[set[str]],
    keep_apart_clusters: list[set[str]],
    fixed_student_ids: set[str],
) -> SeatingHistoryDiversity:
    """Summarize accepted seating checkpoints for anti-repeat scoring."""

    summary = empty_seating_history_diversity()
    for checkpoint in history_checkpoints:
        topology = _checkpoint_topology(checkpoint)
        assignments_by_student = _valid_checkpoint_assignments(
            checkpoint=checkpoint,
            topology=topology,
        )
        if not assignments_by_student:
            continue
        _increment(
            summary.layout_counts,
            normalized_layout_signature(
                assignments_by_student,
                fixed_student_ids=fixed_student_ids,
            ),
        )
        _add_student_reuse_counts(
            summary=summary,
            assignments_by_student=assignments_by_student,
            topology=topology,
            fixed_student_ids=fixed_student_ids,
        )
        _add_keep_near_reuse_counts(
            summary=summary,
            assignments_by_student=assignments_by_student,
            topology=topology,
            keep_near_clusters=keep_near_clusters,
        )
        _add_keep_apart_reuse_counts(
            summary=summary,
            assignments_by_student=assignments_by_student,
            topology=topology,
            keep_apart_clusters=keep_apart_clusters,
        )
    return summary


def normalized_layout_signature(
    assignments_by_student: dict[str, str],
    *,
    fixed_student_ids: set[str],
) -> LayoutSignature:
    """Return a deterministic layout signature, excluding hard fixed students."""

    return tuple(
        sorted(
            (student_id, seat_id)
            for student_id, seat_id in assignments_by_student.items()
            if student_id not in fixed_student_ids
        )
    )


def _checkpoint_topology(checkpoint: SeatingExportCheckpoint) -> SeatTopology:
    checkpoint_seats = [
        Seat.model_validate(seat.model_dump()) for seat in checkpoint.room_context.seats
    ]
    return build_seat_topology(
        seats=checkpoint_seats,
        anchor=infer_teaching_anchor(room_context=checkpoint.room_context),
        fixtures=[
            RoomFixture.model_validate(fixture.model_dump())
            for fixture in checkpoint.room_context.fixtures
        ],
    )


def _valid_checkpoint_assignments(
    *,
    checkpoint: SeatingExportCheckpoint,
    topology: SeatTopology,
) -> dict[str, str]:
    return {
        placement.student_id: placement.seat_id
        for placement in checkpoint.seating_snapshot.placed_assignments
        if placement.seat_id in topology.seats_by_id
    }


def _add_student_reuse_counts(
    *,
    summary: SeatingHistoryDiversity,
    assignments_by_student: dict[str, str],
    topology: SeatTopology,
    fixed_student_ids: set[str],
) -> None:
    for student_id, seat_id in assignments_by_student.items():
        if student_id in fixed_student_ids:
            continue
        _increment_nested(summary.seat_counts_by_student, student_id, seat_id)
        _increment_nested(
            summary.block_counts_by_student,
            student_id,
            topology.block_id_by_seat[seat_id],
        )
        _increment_nested(
            summary.zone_counts_by_student,
            student_id,
            topology.local_zone_id_by_seat[seat_id],
        )
        _increment_nested(
            summary.front_rank_counts_by_student,
            student_id,
            topology.front_rank_by_seat[seat_id],
        )


def _add_keep_near_reuse_counts(
    *,
    summary: SeatingHistoryDiversity,
    assignments_by_student: dict[str, str],
    topology: SeatTopology,
    keep_near_clusters: list[set[str]],
) -> None:
    for cluster in keep_near_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = assignments_by_student.get(left_id)
            right_seat_id = assignments_by_student.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                continue
            pair_key = frozenset((left_id, right_id))
            _increment_nested(
                summary.keep_near_pair_seat_counts,
                pair_key,
                frozenset((left_seat_id, right_seat_id)),
            )
            relation_mode = topology.pair(left_seat_id, right_seat_id).keep_near_relation_mode
            if relation_mode is not None:
                _increment_nested(
                    summary.keep_near_pair_mode_counts,
                    pair_key,
                    relation_mode,
                )


def _add_keep_apart_reuse_counts(
    *,
    summary: SeatingHistoryDiversity,
    assignments_by_student: dict[str, str],
    topology: SeatTopology,
    keep_apart_clusters: list[set[str]],
) -> None:
    for cluster in keep_apart_clusters:
        cluster_key = frozenset(cluster)
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = assignments_by_student.get(left_id)
            right_seat_id = assignments_by_student.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                continue
            _increment_nested(
                summary.keep_apart_pair_seat_counts,
                frozenset((left_id, right_id)),
                frozenset((left_seat_id, right_seat_id)),
            )
        block_signature = _cluster_signature(
            assignments_by_student=assignments_by_student,
            topology=topology,
            cluster=cluster,
            kind="block",
        )
        zone_signature = _cluster_signature(
            assignments_by_student=assignments_by_student,
            topology=topology,
            cluster=cluster,
            kind="zone",
        )
        if block_signature:
            _increment_nested(
                summary.keep_apart_block_signature_counts,
                cluster_key,
                block_signature,
            )
        if zone_signature:
            _increment_nested(
                summary.keep_apart_zone_signature_counts,
                cluster_key,
                zone_signature,
            )


def _cluster_signature(
    *,
    assignments_by_student: dict[str, str],
    topology: SeatTopology,
    cluster: set[str],
    kind: str,
) -> tuple[int, ...]:
    values: list[int] = []
    for student_id in cluster:
        seat_id = assignments_by_student.get(student_id)
        if seat_id is None:
            continue
        if kind == "block":
            values.append(topology.block_id_by_seat[seat_id])
            continue
        values.append(topology.local_zone_id_by_seat[seat_id])
    if len(values) < 2:
        return ()
    return tuple(sorted(values))


def _increment(counts: dict[_Key, int], key: _Key) -> None:
    counts[key] = counts.get(key, 0) + 1


def _increment_nested(
    counts_by_key: dict[_OuterKey, dict[_InnerKey, int]],
    outer_key: _OuterKey,
    inner_key: _InnerKey,
) -> None:
    counts = counts_by_key.setdefault(outer_key, {})
    counts[inner_key] = counts.get(inner_key, 0) + 1
