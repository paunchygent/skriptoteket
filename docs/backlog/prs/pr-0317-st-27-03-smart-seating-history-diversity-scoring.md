---
type: pr
id: PR-0317
title: "ST-27-03: Smart seating history diversity scoring"
status: done
owners: "agents"
created: 2026-05-12
updated: 2026-05-12
stories:
  - "ST-27-03"
  - "ST-27-05"
tags: ["backend", "solver", "history", "simulation", "klassrumskartan", "smart"]
dependencies:
  - "PR-0154"
  - "PR-0307"
  - "PR-0316"
acceptance_criteria:
  - "Given `Smart` and `Historik` are enabled and eligible seating share/export checkpoints exist for the roster and classroom, when the teacher repeatedly creates a new seating draft, runs Smart `Slumpa`, and shares or exports the result, then the solver uses those accepted checkpoints to maximize material variation across full layouts, per-student seat and zone use, `Håll nära` unordered pair placement, and `Håll isär` unordered seat-pair and block spread."
  - "Given the teacher reruns Smart `Slumpa` inside the same active seating draft, when several rule-respecting candidates exist, then the solver prefers a materially different valid result rather than cycling through the same two or three patterns."
  - "Given `Smart` is enabled but no eligible seating checkpoints exist, when the teacher runs Smart `Slumpa`, then the no-history path still produces high-quality varied Smart assignments across repeated same-draft runs without using draft autosave, undo/redo, history-drawer drafts, abandoned drafts, reopened drafts, or public guest local state as Smart history."
  - "Given `Håll nära`, `Håll isär`, and `Närmare läraren` are active together, when Smart seating optimizes variation, then those non-fixed rules remain strong best-effort constraints while historical repetition penalties apply only among valid or near-valid candidates."
  - "Given `Fast plats` rules exist, when Smart seating runs, then fixed placements remain hard seeded assignments and are explicitly excluded from variation expectations while the remaining non-fixed students still rotate as much as the available room permits."
  - "Given the existing G20/SA24D, BF25/G104, and G104 normal-rule simulation fixtures run, when this slice closes, then the fixtures prove same-draft rerun diversity, the G20/SA24D fixture proves new-draft/share-history diversity, the BF25/G104 fixture preserves overlap-rule rotation coverage, and the G104 normal-rule fixture proves 10/10 teacher-visible block patterns without treating in-pair swaps as unique."
---

## Problem

`PR-0307` made authenticated shares count as Smart-history checkpoints, and `PR-0316` made the
first authenticated no-checkpoint Smart run soft-degrade successfully. Production testing with the
`SA24D` roster and `G20` classroom now shows the next scorer problem: after several new seating
drafts are Smart-slumped and then shared/exported, students governed by active rules still collapse
into a small set of repeated layouts.

The implementation currently proves that checkpoints are loaded, but `used_history=true` is not the
same as history-backed fairness. The solver mostly reduces history to teacher-distance averages and
near-teacher pool counts, while `Håll nära`, `Håll isär`, ordinary student seat/zone reuse, and full
assignment hashes do not carry enough historical anti-repeat pressure. The current simulation
coverage also exercises repeated runs by feeding the previous result back as
`current_seat_assignments`, which does not model the teacher workflow of:

1. Create a new seating draft.
2. Run Smart `Slumpa`.
3. Share/export the accepted result.
4. Create another new draft and repeat.

## Goal

Make Smart `Slumpa` as different as possible within the valid search space, both inside one active
draft and across new drafts backed by accepted share/export checkpoints.

The scorer should add history-backed diversity terms for:

- full layout or assignment-hash repetition
- per-student exact-seat reuse
- per-student zone, block, or teacher-distance-band reuse
- `Håll nära` pair seat reuse and local relation reuse
- `Håll isär` unordered pair seat reuse, cluster block/zone reuse, and weak spread patterns

`Fast plats` remains the hard exception: fixed placements are not open to variation, but every
non-fixed student should still rotate around those hard seeds as much as the room allows.

## Non-goals

- No new teacher-facing score panels, sliders, debug views, or solver jargon.
- No change to checkpoint eligibility: draft autosave, undo/redo, history drawers, abandoned
  drafts, reopened drafts, and public guest local state remain ineligible as Smart history.
- No weakening of `Håll nära`, `Håll isär`, or `Närmare läraren` into cosmetic randomness.
- No variation expectation for hard `Fast plats` placements.
- No frontend copy or UI redesign unless an existing Smart-run message is directly wrong after the
  scorer change.
- No grouping scorer redesign in this slice.

## Implementation Plan

1. Add a focused history-diversity scoring context.
   - Keep the domain pure and local to `src/skriptoteket/domain/curated_apps/classroom_planner/`.
   - Derive compact history summaries from `SeatingExportCheckpoint` snapshots rather than querying
     persistence from the solver.
   - Include full-layout repetition, per-student seat/block/zone/band reuse, `Håll nära` unordered
     pair reuse, and `Håll isär` unordered pair-seat plus cluster spread history.

2. Rebalance candidate selection.
   - Keep hard fixed-seat seeding ahead of scoring.
   - Keep `Håll nära`, `Håll isär`, and `Närmare läraren` as quality constraints.
   - Add repetition penalties or diversity bonuses strongly enough to choose materially different
     candidates among rule-respecting layouts, not only exact-score ties.
   - Preserve honest tradeoff detection when rule constraints genuinely narrow the search space.

3. Cover the production workflow in simulations.
   - Extend the current G20/SA24D simulation fixtures to run both same-draft reruns and new-draft
     accepted-checkpoint cycles.
   - Add explicit assertions for distinct full-layout signatures over a 10-run new-draft/share
     cycle.
   - Add a production-shaped G104 normal-rule proof that counts unordered rule-block patterns, so
     swapping students inside the same pair seats does not satisfy the variation requirement.
   - Add per-rule assertions for `Närmare läraren`, `Håll nära`, and `Håll isär` rotation while
     keeping every non-fixed rule valid or documented as a best-effort tradeoff.
   - Add a no-history simulation path proving Smart still varies repeated same-draft runs without
     reading ineligible draft history.
   - Keep or extend BF25/G104 overlap-rule coverage so a student who is both `Närmare läraren` and
     part of another rule still rotates without violating stronger constraints.

4. Add a small live-proof/update path only if needed.
   - If existing Playwright/API proof scripts can be extended safely, add one retained proof for the
     new-draft/share/export history cycle.
   - If local production-like proof requires credentials or live data, keep the automated proof
     fixture-based and document the manual production check separately.

## Test Plan

- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -q --override-ini addopts=''`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver_bf25_g104.py -q --override-ini addopts=''`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_near_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_apart_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_fixed_seats.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py -q`
- If proof script changes: `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Revert the scorer diversity terms and the related simulation/proof assertions together. Do not
replace the checkpoint-backed fairness contract with draft-history fallback or frontend-only
randomization. If the scoring change causes unacceptable rule-quality regressions, keep the
history-summary extraction and tests as evidence but restore the previous scorer weights until a
smaller weighting pass is ready.

## Implementation Summary (2026-05-12)

- Added a pure history-diversity summary for accepted seating checkpoints.
- Added bounded history-backed diversity pressure to candidate scoring for non-fixed layouts,
  per-student seat/block/zone/front-rank reuse, `Håll nära` unordered pair reuse, and `Håll isär`
  unordered seat-pair plus spread-pattern reuse.
- Moved relationship-pair search into a solver-owned search module and now solve two-student
  `Håll isär` pairs jointly, matching the pair-level treatment already used for `Håll nära`.
- Added current-draft block-pattern rotation for `Håll nära` and `Håll isär`, counted by unordered
  teacher-visible blocks rather than in-pair swaps.
- Kept `Fast plats` as hard seeded placement and excluded fixed students from layout and
  per-student variation penalties.
- Added G20/SA24D simulation coverage for the production-shaped new-draft -> Smart `Slumpa` ->
  accepted share/export checkpoint cycle, plus explicit no-history same-draft rerun coverage.
- Preserved BF25/G104 overlap-rule rotation coverage; the overlap fixture keeps all rules valid and
  uses a 10.5 mean-distance floor while prioritizing stronger near-teacher rotation.
- Added a G104 normal-rule 10-run proof for one fixed seat, two near-teacher students, one
  `Håll isär` pair, and one `Håll nära` pair. Both exported-history and same-draft/no-history modes
  produce 10/10 distinct teacher-visible rule block patterns while requiring at least six unordered
  keep-near and keep-apart seat sets.

## Verification (2026-05-12)

- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver_g104_normal_rules.py -q --override-ini addopts=''`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -q --override-ini addopts=''`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver_bf25_g104.py -q --override-ini addopts=''`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_near_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_apart_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_fixed_seats.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py -q`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
