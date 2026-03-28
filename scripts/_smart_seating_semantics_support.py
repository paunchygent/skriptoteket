"""Shared scenario helpers for live smart-seating semantics proof.

This module keeps the live proof entrypoint focused on API orchestration while
holding the fixed G20/SA24D scenario data plus validation logic for the
canonical smart-seating semantics checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any
from uuid import UUID, uuid4

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RoomFixture,
    RoomTemplate,
    Seat,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)

MIN_KEEP_APART_BLOCK_COUNT = 2
MIN_KEEP_APART_MEAN_DISTANCE = 7.0
MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT = 6
MIN_NEAR_TEACHER_ROTATION_POOL_SIZE = 6
SA24D_STUDENT_NAMES = (
    "Kerstin Aitman",
    "Alva Andblad",
    "Sofia Andersson",
    "Elliot Antonsson",
    "Julia Axelsson",
    "Freja Essle",
    "Hilda Grahn",
    "Inger Isfeldt",
    "Nora Johansson",
    "Nellie Jonson",
    "Ella Kjellman",
    "Alexander Klemets",
    "Lucas Kristiansson",
    "Agnes Leandersson",
    "Molly Neijlind",
    "Petter Odehn",
    "Ellen Odenman",
    "Otilia Olofsson Reijer",
    "Vilma Ossner",
    "Mary Parsons",
    "Julia Post",
    "Lily Sandahl",
    "Nora Schneider",
    "Vincent Strandberg Gunnarsson",
    "Leo Svartling",
    "Moa Svensson",
    "Viktor Thornblad",
    "Linnea Walfridson",
    "Liam Vesterberg",
    "Alma Winald",
    "Edith Winlund Strandler",
)
NEAR_TEACHER_STUDENT_IDS = frozenset({"elliot-antonsson", "julia-post"})
KEEP_NEAR_STUDENT_IDS = ("otilia-olofsson-reijer", "mary-parsons")
KEEP_APART_STUDENT_IDS = (
    "petter-odehn",
    "viktor-thornblad",
    "leo-svartling",
    "vincent-strandberg-gunnarsson",
    "lucas-kristiansson",
    "liam-vesterberg",
)


@dataclass(frozen=True)
class RunSummary:
    """Capture one live smart-run sample."""

    revision: int
    assignments_by_student: dict[str, str]
    keep_apart_block_count: int
    keep_apart_mean_distance: float
    layout_signature: tuple[tuple[str, str], ...]


def student_id(name: str) -> str:
    """Normalize one fixture student id for live API payloads."""

    return name.lower().replace(" ", "-")


def build_topology(template_payload: dict[str, Any]) -> SeatTopology:
    """Build live-room topology from the template payload returned by the API."""

    template = RoomTemplate(
        id=UUID(template_payload["id"]),
        owner_user_id=uuid4(),
        name=template_payload["name"],
        grid_cols=template_payload["grid_cols"],
        grid_rows=template_payload["grid_rows"],
        seats=[Seat.model_validate(seat) for seat in template_payload["seats"]],
        fixtures=[RoomFixture.model_validate(fixture) for fixture in template_payload["fixtures"]],
        created_at=_now(),
        updated_at=_now(),
    )
    return build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )


def rotated_assignments(template_payload: dict[str, Any], offset: int) -> list[dict[str, str]]:
    """Return one deterministic rotated history fixture for the live draft."""

    seat_ids = [seat["id"] for seat in template_payload["seats"]]
    rotated_seat_ids = seat_ids[offset:] + seat_ids[:offset]
    return [
        {"student_id": student_id(student_name), "seat_id": seat_id}
        for student_name, seat_id in zip(SA24D_STUDENT_NAMES, rotated_seat_ids, strict=True)
    ]


def near_teacher_pool_seat_ids(topology: SeatTopology) -> frozenset[str]:
    """Return the valid rotating near-teacher pool for the real room."""

    return frozenset(topology.near_teacher_pool(seat_count=len(NEAR_TEACHER_STUDENT_IDS)))


def validate_workspace(
    *,
    workspace: dict[str, Any],
    topology: SeatTopology,
) -> RunSummary:
    """Validate one live smart-run result against the canonical room semantics."""

    assignments = {
        assignment["student_id"]: assignment["seat_id"]
        for assignment in workspace["seat_assignments"]
    }
    if any(
        assignments[student_id] not in near_teacher_pool_seat_ids(topology)
        for student_id in NEAR_TEACHER_STUDENT_IDS
    ):
        raise AssertionError("Near-teacher students left the valid teacher pool.")
    keep_near_pair = topology.pair(
        assignments[KEEP_NEAR_STUDENT_IDS[0]],
        assignments[KEEP_NEAR_STUDENT_IDS[1]],
    )
    if keep_near_pair.keep_near_relation_mode is None:
        raise AssertionError("Keep-near pair lost its compact local relation.")
    keep_apart_pairs = [
        topology.pair(assignments[left_id], assignments[right_id])
        for index, left_id in enumerate(KEEP_APART_STUDENT_IDS)
        for right_id in KEEP_APART_STUDENT_IDS[index + 1 :]
    ]
    if any(pair.orthogonally_adjacent for pair in keep_apart_pairs):
        raise AssertionError("Keep-apart cluster produced an orthogonally adjacent pair.")
    keep_apart_block_count = len(
        {
            topology.block_id_by_seat[assignments[student_id]]
            for student_id in KEEP_APART_STUDENT_IDS
        }
    )
    keep_apart_mean_distance = mean(pair.grid_manhattan for pair in keep_apart_pairs)
    if keep_apart_block_count < MIN_KEEP_APART_BLOCK_COUNT:
        raise AssertionError("Keep-apart cluster collapsed into too few seating blocks.")
    if keep_apart_mean_distance < MIN_KEEP_APART_MEAN_DISTANCE:
        raise AssertionError("Keep-apart cluster lost too much mean pairwise spread.")
    return RunSummary(
        revision=workspace["draft"]["revision"],
        assignments_by_student=assignments,
        keep_apart_block_count=keep_apart_block_count,
        keep_apart_mean_distance=keep_apart_mean_distance,
        layout_signature=tuple(sorted(assignments.items())),
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)
