---
type: reference
id: REF-klassrumskartan-solver-rule-diagnostics-contract-2026-05-10
title: "Klassrumskartan solver rule diagnostics contract"
status: active
owners: "agents"
created: 2026-05-10
updated: 2026-05-10
topic: "klassrumskartan-solver-diagnostics"
links:
  [
    "EPIC-27",
    "ST-27-09",
    "ST-29-12",
    "ST-29-16",
    "ST-29-17",
    "PR-0314",
    "REF-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25",
    "REF-symbol-semantics-inventory-and-decision-contract-2026-05-04",
  ]
---

## Purpose

Klassrumskartan map markers need success, degraded, pending, and failed states
for teacher trust, but those states must be solver-owned. The frontend must not
infer soft-rule truth from geometry, CSS layout, or duplicated TypeScript rule
checks.

This contract defines the backend diagnostic vocabulary that should power
future colored rule markers on phone, tablet, and desktop classroom maps.

## Status Vocabulary

Every rule diagnostic should expose one canonical status.

| Status | Marker tone | Meaning |
|---|---|---|
| `pending` | warning | The rule cannot be evaluated because a required student, seat, or placement is missing. |
| `satisfied` | success | The desired/optimal outcome for the rule has been achieved. |
| `degraded` | warning | The outcome is acceptable, but it is not the desired/optimal rule outcome. |
| `failed` | error | The outcome is outside the acceptable range, violates a hard rule, or creates an immediate conflict. |

Frontend mapping is intentionally mechanical:

- `pending` -> warning token family
- `satisfied` -> success token family
- `degraded` -> warning token family
- `failed` -> error token family

The frontend may render a neutral marker only when no solver-owned diagnostic
exists yet.

## Diagnostic Shape

The public/authenticated Smart seating result should gain an additive
diagnostic list. The exact DTO names may follow backend conventions, but the
shape should preserve these concepts:

```text
rule_id: string | null
rule_kind: fixed_seat | near_teacher | keep_near | keep_apart
status: pending | satisfied | degraded | failed
student_ids: string[]
seat_ids: string[]
reason_code: string
relation_mode?: adjacent-row | adjacent-column | diagonal-block | one-step-row | one-step-column | none
seating_context?: shared_table | bench_row | row_layout | local_cluster | unknown
message_key?: string
```

Do not expose raw score values to the frontend. Use stable categories and
reason codes instead.

## Seating Context

`Håll nära` needs seating context because the same geometry means different
things in different classroom layouts.

| Context | Meaning | Expected source |
|---|---|---|
| `shared_table` | Seats are attached to the same round or square table. Across-table proximity can be an intended close placement. | `RoomFixtureType.ROUND_TABLE` or `RoomFixtureType.SQUARE_TABLE` support fixture grouping. |
| `bench_row` | Seats belong to a bench-supported row. Pair success should prefer same-row left/right adjacency. | `RoomFixtureType.BENCH` support fixture grouping. |
| `row_layout` | Seats are not table-supported but form row/column classroom layout through topology. | Seat topology without table support fixture. |
| `local_cluster` | Seats form a compact local component, but context is not strong enough to call it table or row. | `SeatTopology.local_zone_id_by_seat`. |
| `unknown` | The solver cannot classify the context safely. | Fallback only. |

The backend already computes `same_block`, `same_local_zone`, and relation
modes. The next implementation should extend topology so pair diagnostics can
distinguish table-supported blocks from bench/row-supported blocks.

## Fixed Seat Semantics

`Fast plats` is a hard rule.

| Condition | Status | Reason code |
|---|---|---|
| Target student is unplaced or target seat is empty | `pending` | `fixed_seat_waiting_for_assignment` |
| Target student sits in target seat | `satisfied` | `fixed_seat_exact` |
| Target seat has another student | `failed` | `fixed_seat_wrong_student_in_seat` |
| Target student sits in another seat | `failed` | `fixed_seat_student_elsewhere` |
| Rule references missing student/seat/template | `failed` | `fixed_seat_invalid_reference` |

No `degraded` state is needed for fixed seats.

## Keep Near Semantics

`Håll nära` needs pair-specific and group-specific diagnostics.

### Pair Rule

For exactly two students, diagnose the pair directly.

| Context | Relation | Status | Reason code |
|---|---|---|---|
| `shared_table` | `adjacent-row` or `adjacent-column` | `satisfied` | `keep_near_shared_table_adjacent` |
| `shared_table` | table-opposite/across relation represented by `adjacent-column` in the active topology | `satisfied` | `keep_near_shared_table_across` |
| `shared_table` | `diagonal-block` or `one-step-*` | `degraded` | `keep_near_shared_table_compact_tradeoff` |
| `bench_row` / `row_layout` | `adjacent-row` | `satisfied` | `keep_near_row_adjacent` |
| `bench_row` / `row_layout` | `adjacent-column`, `diagonal-block`, or `one-step-*` | `degraded` or `failed`, chosen by backend proof | `keep_near_row_non_adjacent_tradeoff` or `keep_near_row_not_close` |
| any | `none` | `failed` | `keep_near_not_close` |
| any | one or both students unplaced | `pending` | `keep_near_waiting_for_assignment` |

The row-layout decision is deliberately left as a backend proof point. The
implementation must add tests before deciding whether across-row pair placement
in row layout is `degraded` or `failed`.

### Group Rule

For three or more students, do not require every pair to be left/right
adjacent. A group can be successful when it forms a context-appropriate compact
cluster even if not every pair is directly adjacent.

Suggested group classification:

- `satisfied`: the group occupies one context-appropriate compact placement.
  For `shared_table`, this means the students are seated at the same round or
  square table where the rule intent reads as "together at this table." For
  `bench_row` / `row_layout`, this means the group reads as a compact row or
  local row cluster rather than requiring every pair to be left/right adjacent.
- `degraded`: the group is mostly compact but has one or more non-ideal pair
  relations.
- `failed`: the group is split across unrelated blocks/zones or has isolated
  members.
- `pending`: one or more students are unplaced.

Stop rules:

- Groups of three or four students should receive the most precise
  context-aware classification. Shared-table groups should be `satisfied` only
  when the students are at the same table; nearby or adjacent tables are not the
  same teacher intent and should be `failed` unless the backend proves a
  narrower degraded case.
- Groups of five or six students may still be classified when they fit one
  natural table/support cluster or a visibly compact row/local cluster. If the
  placement is partly compact but strained, prefer `degraded` over pretending it
  is fully satisfied.
- Groups larger than six students are outside precise diagnostic scope. The
  solver may still try to keep them close, but diagnostics should not claim an
  exact satisfied/failed judgment. Use `degraded` with
  `keep_near_group_too_large_for_precise_diagnostic`.

Display copy for the large-group stop rule:

> För stor grupp för {aktuell regel} att hantera. Minska antalet elever för
> bättre resultat.

Backend implementation should compute group status from topology and then may
include pair details for explanation/debugging. The frontend should use the
group diagnostic status for marker tone.

## Keep Apart Semantics

`Håll isär` should mirror the current solver's hard-negative boundary.

| Condition | Status | Reason code |
|---|---|---|
| Orthogonal adjacency or diagonal contact | `failed` | `keep_apart_immediate_contact` |
| Same block/local zone but not immediate contact | `degraded` | `keep_apart_same_zone_tradeoff` |
| Different block/zone or enough front/lateral distance | `satisfied` | `keep_apart_separated` |
| One or more students unplaced | `pending` | `keep_apart_waiting_for_assignment` |

## Near Teacher Semantics

`Nära läraren` should use the canonical teaching anchor plus seating context.
It must not treat lateral distance from the teacher position as a reason to
downgrade a normal row/bench first-row seat.

| Condition | Status | Reason code |
|---|---|---|
| Student is unplaced | `pending` | `near_teacher_waiting_for_assignment` |
| `bench_row` / `row_layout` seat is in the first row for its column relative to the teaching edge | `satisfied` | `near_teacher_row_first_rank` |
| `bench_row` / `row_layout` seat is in the next front rank | `degraded` | `near_teacher_row_front_compromise` |
| `shared_table` seat belongs to one of the two table support groups closest to the teaching anchor | `satisfied` | `near_teacher_table_closest_groups` |
| `shared_table` seat belongs to the next closest table support group | `degraded` | `near_teacher_table_compromise_group` |
| Seat is outside acceptable proximity | `failed` | `near_teacher_too_far` |

The acceptable band must be backend-owned. Do not let the frontend derive it
from raw coordinates. Inside a satisfied row/bench front rank, lateral distance
may only be a deterministic tie-breaker or history/fairness input; it must not
turn a first-row seat into a degraded seat. For table contexts, rank table
support groups by teaching-anchor proximity rather than individual raw seat
coordinates so all seats at the same qualifying table share the same status.

## Implementation Guidance

1. Keep the current neutral frontend soft-rule markers until diagnostics are
   available.
2. Add domain-level diagnostic helpers close to `seat_topology.py`,
   `smart_seating_scoring.py`, or a new focused domain module if that keeps
   files under the repository size/SRP boundary.
3. Add backend unit tests before exposing DTOs.
4. Add diagnostics additively to authenticated and public Smart seating
   handlers.
5. Update frontend marker rendering only after backend diagnostics are covered
   by tests and available in the planner state.

## Required Backend Proof Cases

- Fixed seat exact, empty/pending, wrong occupant, and invalid reference.
- `Håll nära` pair at a shared table where across-table placement is
  `satisfied`.
- `Håll nära` pair in row/bench layout where left/right adjacency is
  `satisfied`.
- `Håll nära` pair in row/bench layout where across/diagonal placement is
  proven as either `degraded` or `failed` by the accepted backend rule.
- `Håll nära` group of three or more students in one compact local zone.
- `Håll nära` group split across unrelated zones.
- `Håll isär` immediate contact, same-zone tradeoff, and separated states.
- `Nära läraren` in-pool, front-band tradeoff, too-far, and unplaced states.
