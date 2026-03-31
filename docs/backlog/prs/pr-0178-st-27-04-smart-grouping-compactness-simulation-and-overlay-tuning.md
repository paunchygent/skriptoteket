---
type: pr
id: PR-0178
title: "Klassrumskartan: smart grouping compactness simulation and seating-map overlay tuning"
status: in_progress
owners: "agents"
created: 2026-03-30
updated: 2026-03-31
stories:
  - "ST-27-04"
tags: ["backend", "simulation", "planner", "klassrumskartan", "grouping"]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0154"
  - "PR-0167"
acceptance_criteria:
  - "Given the grouping solver evaluates compactness candidates, when one candidate would create uneven group sizes, then it is rejected before compactness scoring so final group sizes never differ by more than one student."
  - "Given the compactness lane needs tuning, when the first simulation pass runs, then it uses whole-class seating projections rather than sparse tracked seating pairs as the classroom-aware input."
  - "Given keep-apart students still need to be absorbed into coherent nearby groups, when the next compactness pass runs, then the solver adds one topology-aware post-separation cohesion penalty instead of relying on pairwise Manhattan distance alone."
  - "Given one simulation scenario runs, when operator artifacts are written, then the output includes rough seating-map overlays where each student is rendered at their seat and group-local splashes or islands remain visible."
  - "Given one simulation candidate is rendered, when one group occupies multiple disconnected seat regions, then the overlay shows multiple separate group-region boxes rather than one misleading room-wide rectangle."
  - "Given a candidate creates disconnected same-group islands, when topology-aware cohesion scoring runs, then extra components, singleton components, and distant secondary clusters are penalized separately so the comparison can reveal which term improves the overlay."
  - "Given multiple compactness parameter candidates are compared, when the summary artifact is written, then it reports explicit-rule validity, compactness spread metrics, and group-component counts alongside the generated PNG overlays."
  - "Given canonical classroom scenarios already exist for smart seating and grouping, when the simulation lane is implemented, then it reuses those same named classrooms and rosters rather than inventing toy fixtures."
  - "Given the next tuning pass completes, when we inspect the artifacts, then we can compare a no-compactness baseline, a quadratic-only candidate, and at least two topology-aware anti-island candidates for the same seating map."
  - "Given canonical rooms differ structurally, when we inspect the overlays, then the tuning lane can compare block-fit candidates for table-bound rooms instead of assuming one compactness curve works equally well across benches and table islands."
  - "Given greedy search order can change compactness outcomes, when the simulation report runs, then each candidate is evaluated across repeated randomized trials, the best found layout is rendered, and the summary reports the success rates instead of only one lucky run."
---

## Problem

`PR-0167` locks the smart-grouping precedence model, but it intentionally leaves the exact
classroom-aware compactness curve tunable through simulations. The current grouping simulation lane
now gives us whole-class seating overlays, but it still exposes one meaningful gap:

- it proves rules and history behavior
- it reuses canonical seat coordinates
- it shows when quadratic spread penalties reduce average distances
- but it still allows keep-apart students to land as spatial islands because the solver only scores
  pairwise spread and not post-separation group cohesion on the topology graph

Without one explicit anti-island lane, we can lower mean distances while still producing visually
fragmented groups that teachers would judge as poor local clusters. The first pass also exposed that
different room structures need different compactness signals: `G20` behaves like connected bench
blocks, while `G104` behaves like six 4-seat table islands.

## Goal

Add the next compactness-tuning simulation lane for `ST-27-04` so we can compare grouping
candidates on top of a full seating map and judge whether topology-aware anti-island penalties help
the classroom-aware lane produce compact local group regions without violating stronger rules.

## Non-goals

- Shipping new teacher-facing compactness controls.
- Freezing the final compactness constants permanently from one run.
- Turning the simulation overlay into a polished product UI.
- Replacing the existing rule/history solver tests.

## Implementation plan

1. Add one simulation/reporting lane on top of the canonical smart-grouping scenarios.
   - Reuse the existing named classrooms and rosters already used by the smart seating/grouping
     simulations.
   - Build full-class seating projections instead of sparse tracked-pair seating hints.

2. Extend the compactness model beyond pairwise spread.
   - Keep production defaults reviewable through explicit config.
   - Add one topology-aware post-separation cohesion lane that can penalize:
     - disconnected same-group components
     - singleton components
     - distant secondary clusters relative to the nearest same-group cluster
   - Keep explicit rules and balanced sizes ahead of that lane.
  - Add room-structure lanes for both table-block and bench-chain experiments so table-bound rooms
    and corridor/bench rooms can reward different local shapes instead of sharing one generic
    compactness signal.
  - Add one post-construction local-improvement phase after the greedy assignment pass so the
    solver can try pair swaps across groups and keep the single best improving full-score swap
    before the report renders the candidate.

3. Parameterize compactness tuning for simulation runs.
   - Allow the simulation harness to sweep:
     - elastic radius
     - quadratic overflow penalty
     - medoid-based center-distance falloff
     - optional local proximity reward
     - disconnected-component penalties
     - singleton penalties
     - nearest-cluster penalties
   - Run repeated randomized greedy trials per candidate and keep both:
     - the best found layout for visual review
     - the aggregate rule/compactness hit rates for robustness comparisons

4. Generate operator-facing overlay artifacts.
   - Render one rough seating map where each seated student is one square.
   - Color student squares by assigned group.
   - Draw separate region boxes for disconnected same-group seat components.
   - Keep row and column spacing visible so islands and splashes read immediately.

5. Write one machine-readable summary artifact for each run set.
   - Report explicit-rule validity.
   - Report within-group spread metrics.
   - Report disconnected component counts per group.
    - Report singleton-island counts and nearest-cluster spread where applicable.
   - Report split-block group counts and secondary-block spill so table-fit tradeoffs are visible.
   - Compare baseline vs compactness candidates for the same seating map.

6. Run the next simulation pass and capture the resulting artifacts in `.artifacts/`.

## Test plan

- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver.py tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver_g20_sa24d.py tests/unit/domain/curated_apps/classroom_planner/test_smart_grouping_solver_bf25_g104.py -q`
- `pdm run python -m scripts.smart_grouping_compactness_simulation_report`
- `pdm run docs-validate`

## Rollback plan

- Revert the simulation/reporting lane and compactness parameterization together while leaving the
  shipped grouping smart-run contract intact.

## Current findings (2026-03-31)

- The focused repeated-trial sweep now compares `baseline`, `quadratic`, `quadratic + mittpunkt`,
  `quadratic + delytor`, `quadratic + bänkkedja`, and `hybrid-all` across `10` randomized trials
  with `8` extra greedy-order attempts inside each trial.
- The `G20 / SA24D` simulation slice now uses the reduced 4-student keep-apart cluster
  (`Petter Odehn`, `Viktor Thornblad`, `Leo Svartling`, `Vincent Strandberg Gunnarsson`) for both
  the projected seating map and the grouping rules so the comparison stays internally consistent.
- The solver search is now cheaper and less misleading:
  - greedy construction still explores multiple student orders
  - one final cross-group pair-swap pass repairs obvious misses such as
    `Lucas Kristiansson ↔ Hilda Grahn`
  - the report no longer depends on a long repeated hill-climb to expose those fixes
- `BF25 / G104` remains effectively solved by the quadratic family:
  - `quadratic`, `quadratic + mittpunkt`, and `quadratic + delytor` all still hit `1.00` on
    explicit-rule validity, zero-fragmentation, zero-singleton, and zero-split-block rates
  - the new bench-chain lane is not helpful there; it weakens robustness because `G104` behaves as
    table islands rather than benches
- `SA24D / G20` is still the hard room, but the comparison is now more topology-truthful:
  - all focused candidates preserved the explicit grouping rules
  - none achieved a non-zero fragment-free rate across the repeated sweep
  - the new bench-chain lane reduced zone spill and made the report measure corridor/bench shape
    explicitly, but it did not outperform the best quadratic-family layouts yet
  - current best-of-trial tradeoffs are:
    - `quadratic + mittpunkt`: mean within-group distance `1.82`, max `4`, `2` fragmented groups;
      this is the current preferred lane
    - `quadratic + delytor`: mean `1.93`, max `6`, `2` fragmented groups, slightly more truthful
      anti-island behavior
    - `quadratic + bänkkedja`: mean `1.91`, max `5`, `2` fragmented groups, better bench-shape
      measurement but no actual G20 breakthrough
- The next tuning pass should keep `G104` stable and focus only on `G20` bench rooms:
  - reduce tail students at the ends of bench chains
  - reward denser dominant-zone absorption without over-penalizing valid cross-row local clusters
