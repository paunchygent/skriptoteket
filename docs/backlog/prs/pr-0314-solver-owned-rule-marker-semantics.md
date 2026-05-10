---
type: pr
id: PR-0314
title: "Solver-owned rule marker semantics"
status: in_progress
owners: "agents"
created: 2026-05-10
updated: 2026-05-10
stories:
  - "ST-27-09"
  - "ST-29-12"
  - "ST-29-16"
  - "ST-29-17"
tags: ["frontend", "backend", "ux", "klassrumskartan", "smart-rules", "symbols"]
dependencies:
  - "PR-0310"
links:
  - "REF-klassrumskartan-solver-rule-diagnostics-contract-2026-05-10"
acceptance_criteria:
  - "Given a visible rule marker represents a soft solver rule, when the frontend renders the marker, then success, warning, and error tones come from solver-owned diagnostics or are not shown as fulfillment truth."
  - "Given `Håll nära` places two students across a relation that the solver treats as acceptable or as a tradeoff, when markers render, then the frontend does not independently mark the pair as a hard red conflict."
  - "Given `Nära läraren` is evaluated, when marker tones render, then the frontend does not use a separately maintained teacher-zone rule that can drift from the backend topology/scoring contract."
  - "Given no solver-owned per-rule diagnostic exists for a soft rule, when a map renders, then the marker may show rule participation but not a misleading fulfilled/conflict state."
  - "Given fixed-seat markers render, when the assigned student sits in or outside the exact fixed seat, then the direct hard-rule marker may still use local exact-seat truth."
  - "Given backend diagnostics are added, when `Håll nära` is evaluated, then pair and group outcomes distinguish desired success, acceptable degraded placement, and failed placement using backend topology and seating context."
  - "Given students sit at a shared round or square table, when a `Håll nära` pair is placed across the table in a backend-approved close relation, then the diagnostic can classify that as `satisfied` rather than a row-layout failure."
  - "Given students sit in bench or row layout, when a `Håll nära` pair is not left/right adjacent, then the backend diagnostic classifies it as degraded or failed according to the accepted row-layout rule and proves that with unit tests before frontend coloring."
  - "Given a seating workspace is reloaded or rehydrated after a Smart seating run, when the current persisted draft, smart-rule shape, template, roster, and seat assignments still match the solver input, then backend-owned rule diagnostics are recomputed and returned so soft-rule marker tones survive reload without persisting stale diagnostic blobs."
  - "Given diagnostics are returned from workspace load or Smart-run responses, when the frontend maps them to marker tones, then every diagnostic carries a freshness key or digest derived from draft revision, smart-rule shape, template, roster, and seat assignments, and stale or mismatched diagnostics render neutral."
---

## Problem

`PR-0310` added compact symbolic rule markers to map seats. Post-deploy phone
testing shows that the marker tones can contradict the Smart solver's actual
relationship semantics:

- `Nära läraren` can show green or amber based on a frontend teacher-zone pool
  rather than the solver's actual scoring and rotation context.
- `Håll nära` can show red when students are placed in a relation the solver
  still treats as acceptable or as a soft tradeoff rather than a hard conflict.

The current frontend marker helper has become a second rule engine. That is
unsafe because any backend solver refinement can make the visual marker truth
drift.

## Goal

Move rule-marker fulfillment semantics back to the solver boundary.

The frontend should render symbols, labels, and layout. It must not invent hard
success/warning/error truth for soft solver rules unless that truth comes from
the canonical solver or from a deliberately shared diagnostic contract.

## Non-goals

- No marker layout redesign beyond tone/semantics correction.
- No new symbol family; use the existing `ST-29-12` symbol language.
- No change to fixed-seat hard-rule persistence.
- No solver scoring rewrite.
- No attempt to expose raw numeric solver scores directly to teachers.

## Design Direction

Use a two-step remediation path.

### Step A: Stop Misleading Soft-Rule Tones

As the immediate trust fix, keep rule symbols visible but remove local
success/warning/error claims for soft rules unless the state is direct and
unambiguous.

- `Fast plats`: may keep exact-seat local truth because the hard rule is a
  direct comparison between rule student, rule seat, and current assignment.
- `Nära läraren`, `Håll nära`, `Håll isär`: render as participation/diagnostic
  markers only unless solver-owned diagnostics are present.
- Red/error must be reserved for actual hard conflicts or solver-owned conflict
  diagnostics.

### Step B: Add Solver-Owned Diagnostics

Add an additive diagnostics contract to the Smart seating result when the team
needs visible fulfillment truth. The governing reference is
[`REF-klassrumskartan-solver-rule-diagnostics-contract-2026-05-10`](../../reference/ref-klassrumskartan-solver-rule-diagnostics-contract-2026-05-10.md).

- rule id or stable rule key
- affected student ids and seat ids
- rule kind
- canonical status: `pending`, `satisfied`, `degraded`, or `failed`
- optional relation mode for `Håll nära`, using backend topology language such
  as `adjacent-row`, `adjacent-column`, `diagonal-block`, `one-step-row`, or
  `one-step-column`
- optional seating context for `Håll nära`, such as `shared_table`,
  `bench_row`, `row_layout`, `local_cluster`, or `unknown`
- optional display-safe explanation category, not raw scoring internals

The frontend marker helper then maps diagnostics to existing symbols and token
families. It does not recompute solver truth.

### Step C: Rehydrate Diagnostics From Current Truth

Solver diagnostics must not remain a Smart-run-only transient payload. The
workspace load path must recompute diagnostics from the current persisted truth
instead of storing diagnostic blobs in draft data:

- draft id and revision
- current smart-rule shape and revision
- current room template id and seat/furniture shape
- current roster id and student ids
- current seat assignments

The recomputed diagnostics must carry a display-safe freshness key or digest
covering those inputs. The frontend may color soft-rule markers only when the
diagnostic freshness key matches the current visible workspace inputs. If the
key is absent or mismatched, the marker must render neutral.

This rehydration requirement applies to authenticated workspace load and any
public/guest workspace rehydration surface that can restore a seating workspace
after a browser reload. It is not enough to clear diagnostics on mutation:
reload must be able to regain truthful solver-owned marker tones from backend
truth.

`Håll nära` requires special care:

- pairs at shared round/square tables can treat across-table relation as a
  backend-approved success state
- pairs in bench/row layout should prefer left/right adjacency as the true
  desired success state
- groups of three or more students should be diagnosed as compact clusters,
  not as an impossible "all pairs adjacent" requirement
- group diagnostics must remain context-aware: shared-table groups should only
  count as satisfied when they are at the same table, while row/bench groups
  should be judged as compact row/local clusters
- oversized keep-near groups must use the stop-rule copy from the diagnostics
  reference: "För stor grupp för {aktuell regel} att hantera. Minska antalet
  elever för bättre resultat."
- row-layout across/diagonal pair placements must be decided and proved in the
  backend before the frontend receives any red/amber/green marker state

`Nära läraren` also requires context-aware backend semantics:

- row/bench layouts should treat first-row seats in every column as satisfied,
  regardless of lateral distance from the teaching anchor
- row/bench next-front-rank seats are the degraded front-zone compromise
- table layouts should treat seats at the two table support groups closest to
  the teaching anchor as satisfied
- table layouts may use the next closest table support group as the degraded
  compromise
- the frontend must render only the backend diagnostic status

## Frontend Entry Points

- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSeatRuleMarkers.ts`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerPhoneClassroomSeatMap.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesSeatNode.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/SeatNode.vue`

## Backend Entry Points

- `src/skriptoteket/domain/curated_apps/classroom_planner/seat_topology.py`
- `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating_scoring.py`
- `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating_candidate_scoring.py`
- `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/handlers/smart_seating.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_smart_seating.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py`
- `src/skriptoteket/web/api/v1/apps_classroom_planner.py`
- `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/smart_rule_diagnostic_contracts.py`
- `frontend/apps/skriptoteket/src/api/openapi.d.ts`

## Implementation Plan

1. Update marker tests to prove soft rules no longer receive hard conflict
   tones from frontend-only distance checks.
2. Remove frontend local fulfillment classification for `Nära läraren`,
   `Håll nära`, and `Håll isär`.
3. Preserve fixed-seat hard-rule marker behavior where it reflects exact local
   state.
4. Implement Step B as a backend-first diagnostic contract:
   - add a focused diagnostic domain module or helpers without bloating the
     solver modules beyond the file-size/SRP boundary
   - extend topology with seating context where needed
   - return additive diagnostics from authenticated and public Smart seating
     handlers
5. Implement Step C backend rehydration:
   - recompute diagnostics on authenticated workspace load from persisted
     draft, smart rules, template, roster, and seat assignments
   - include a freshness key or digest over draft revision, smart-rule shape,
     template, roster, and seat assignments
   - expose the same additive diagnostic contract on workspace load without
     persisting diagnostic blobs as draft state
   - update public/guest rehydration only if the guest restore path can receive
     backend recomputed diagnostics; otherwise document why guest diagnostics
     stay neutral until the next public Smart run
6. Add backend tests for fixed seat, near-teacher, keep-apart, and keep-near
   pair/group outcomes before frontend coloring is restored.
7. Only after backend diagnostics pass, let the frontend map diagnostic status
   to marker tones.
8. Regenerate OpenAPI frontend types after adding `rule_diagnostics` to
   workspace load responses and fail the slice if generated `openapi.d.ts`
   drifts from the backend response model.
9. Keep marker symbols, layout, accessible labels, and collision avoidance from
   `PR-0310`.

## Test Plan

- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers PlannerPhoneClassroomSeatMap PlannerRulesSeatNode RoomCanvas`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/application/apps/classroom_planner/test_public_smart_run.py -q`
- Add focused backend tests for the diagnostic contract named in
  `REF-klassrumskartan-solver-rule-diagnostics-contract-2026-05-10`.
- Add backend/API tests proving workspace load returns recomputed diagnostics
  with a freshness key, and that a changed draft revision, smart-rule shape,
  template, roster, or seat assignment changes or invalidates that key.
- `pdm run fe-gen-api-types`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback Plan

Revert marker-semantics changes while preserving the `PR-0310` compact marker
layout and Smart outcome toast-copy improvements.

## Implementation Closeout

Step A implemented on 2026-05-10.

- Removed frontend-only near-teacher pool calculation from
  `classroomPlannerSeatRuleMarkers.ts`.
- Removed frontend-only keep-near / keep-apart fulfillment classification from
  `classroomPlannerSeatRuleMarkers.ts`.
- Soft-rule markers for `Nära läraren`, `Håll nära`, and `Håll isär` now render
  as neutral participation markers unless a future solver-owned diagnostic
  contract supplies fulfillment truth.
- Fixed-seat markers keep exact local success/warning/error tones because that
  hard rule compares the current occupant against one explicit target seat.

Verification:

- `pdm run fe-test -- --run useRoomTouchViewportGestures RoomTemplateBuilderSurface PlannerPhoneClassroomSeatMap PlannerPhoneFixedSeatRulePanel PlannerSeatingWorkspacePane RoomCanvas PlannerRulesMapCanvas PlannerRulesSeatNode`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

Step B implemented on 2026-05-10.

- Added solver-owned diagnostics through
  `smart_rule_diagnostics.py`, `seat_support_context.py`, and additive
  authenticated/public Smart seating response contracts.
- `Nära läraren` diagnostics now use solver-side room context: row and bench
  layouts treat the first rank in each local column as satisfied, while table
  layouts use the two closest table support groups as satisfied.
- `Håll nära` diagnostics now distinguish row/bench pairs, shared-table pairs,
  compact groups, visibly split groups, and oversized stop-rule groups using
  backend topology rather than frontend assumptions.
- `Håll isär` diagnostics now distinguish immediate contact conflicts from
  degraded same-lane compromises and satisfied separation.
- The frontend now maps diagnostic status to marker tones only when the
  diagnostic still matches the visible student/seat assignment; stale or absent
  soft-rule diagnostics render neutral markers.
- The G20 / SA24D room-scale simulation proof was split into a scenario helper
  so the test modules remain inside the <500 LoC SRP boundary.

Additional verification:

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/application/apps/classroom_planner/test_public_smart_run.py -q`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_rule_diagnostics.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_near_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_apart_geometry.py -q`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -m simulation --override-ini addopts='' -q`
- `pdm run fe-test -- --run RoomCanvas PlannerPhoneFixedSeatRulePanel PlannerRulesMapCanvas useSmartSeatingRun usePublicSmartSeatingRun`
- `pdm run ruff check ...`

Second-pass remediation applied on 2026-05-10.

- Direct smart-rule mutations now receive the shared diagnostics invalidation
  callback and clear stored solver diagnostics before marking the smart-rule
  lane dirty.
- The direct mutation proof covers near-teacher edits, relationship-rule
  commits, fixed-seat commits, and Smart preference changes in
  `classroomPlannerSmartRuleActions.spec.ts`.
- The near-limit frontend files were split rather than compressed:
  `classroomPlannerFixedSeatRuleActions.ts`,
  `classroomPlannerDerivedState.ts`,
  `classroomPlannerGuestDraftHistoryActions.ts`,
  `phoneClassroomSeatMapLayout.ts`, and
  `useClassroomPlannerRuleDiagnostics.ts`.

`PR-0313` still remains open for actual iPhone confirmation before deploy
closeout.

## Review Closeout

Ruthless review on 2026-05-10 requested changes. `PR-0314` was blocked until:

- stale solver diagnostics cannot keep coloring markers after local rule edits
  or rule-shape changes
- row/bench `Håll nära` pair placement proves direct same-row adjacency as the
  clean no-conflict outcome instead of rotating into same-column placement
  under light rule pressure

See
[`REV-PR-0314`](../reviews/review-pr-0314-solver-owned-rule-marker-semantics.md).

## Review Remediation

Applied on 2026-05-10; second-pass review keeps `PR-0314` in progress until the
remaining diagnostic lifecycle gap is closed.

- Marker coloring now requires a full current soft-rule shape match before a
  diagnostic can supply a tone: relationship diagnostics must match current
  rule id, rule kind, current `student_ids`, and current student-seat
  assignment; near-teacher diagnostics must match the current stable
  `near_teacher:{student_id}` preference key and assignment.
- Authenticated and guest local assignment/template/roster mutations clear the
  stored diagnostics so stale solver output is not carried across visible local
  workspace changes.
- Row/bench and unknown-context `Håll nära` pair scoring now treats
  `adjacent-row` as the clean target and heavily penalizes `adjacent-column`
  unless the pair is explicitly in a shared-table context.
- The G20 / SA24D solver proof now asserts the keep-near pair remains
  `adjacent-row` across history reruns while still preserving near-teacher,
  keep-apart, and overall layout diversity.

Second-pass review accepted the row/bench `Håll nära` remediation and the
specific rule-shape diagnostic matching proof. It still requires stored
diagnostics to be cleared or revision-checked on every local smart-rule
mutation, not only on assignment/template/roster mutations. The bundled
`PR-0313` phone pinch lane also remains open until actual iPhone confirmation is
recorded.

## Field Follow-up: Diagnostic Rehydration

Real-device follow-up on 2026-05-10 confirmed that soft-rule marker tones are
lost after reloading the seating workspace. Fixed-seat markers keep their green
state because they are recomputed locally from exact hard-rule truth, but
`Nära läraren`, `Håll nära`, and `Håll isär` colors depend on transient
solver diagnostics that are currently applied only from Smart-run responses.

Required remediation:

- Do not persist diagnostic blobs in draft state.
- Recompute solver-owned diagnostics on authenticated workspace load from the
  current persisted draft, smart rules, template, roster, and seat assignments.
- Return the recomputed diagnostics additively from the workspace response.
- Attach a freshness key or digest over draft revision, smart-rule shape,
  template, roster, and seat assignments.
- Require the frontend marker mapper to treat missing or mismatched freshness
  as neutral, not as stale success/warning/error truth.
- Regenerate and check OpenAPI frontend types because `rule_diagnostics` moving
  onto workspace load is an API contract change.

Proof must cover reload/rehydration directly: after a Smart seating run creates
soft-rule diagnostics, reloading the same seating workspace should restore the
same solver-owned marker tones without running Smart again, and any changed
freshness input should neutralize or replace those diagnostics.

Verification:

- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers PlannerPhoneClassroomSeatMap useRoomTouchViewportGestures`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_near_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_rule_diagnostics.py -q`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -m simulation --override-ini addopts='' -q`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_near_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -m simulation --override-ini addopts='' -q`

## Rehydration Remediation Closeout

Implemented on 2026-05-10; ready for retained review after verification.

- Added a focused diagnostic freshness helper that builds a canonical SHA-256
  key from diagnostic schema version, draft id/revision, smart-rule
  revision/shape, template seat/furniture shape, roster/student ids, and sorted
  seat assignments.
- Extended `SmartRuleDiagnosticDto` with additive `freshness_key` and attached
  the key to authenticated Smart-run diagnostics, public Smart-run diagnostics,
  and authenticated seating-workspace reload diagnostics.
- `GET /drafts/{draft_id}/workspace` now recomputes seating rule diagnostics
  from current persisted truth instead of persisting diagnostic blobs in draft
  data. Grouping workspaces return an empty diagnostic list and do not touch the
  smart-rule repository.
- Frontend workspace hydration now applies returned `rule_diagnostics`; local
  workspace clears and save acknowledgements without diagnostics neutralize
  stored diagnostic colors.
- Soft-rule marker coloring now requires a backend freshness key plus current
  rule kind/student-shape and current student-seat assignment matches. Missing
  freshness renders neutral, so stale transient diagnostics cannot keep coloring
  after reload or local edits.
- Regenerated OpenAPI frontend types with `pdm run fe-gen-api-types`; generated
  `openapi.d.ts` now includes `rule_diagnostics` on workspace responses and
  `freshness_key` on diagnostic DTOs.

Public/guest decision:

- Public Smart-run responses now carry the same freshness key.
- A new stateless public diagnostic-rehydrate endpoint is intentionally not
  introduced in this slice because the current reported reload issue is the
  authenticated persisted-draft workspace. Browser-owned public snapshots
  should remain neutral unless they pass through a backend Smart-run or an
  explicitly scoped future public rehydrate API.

Additional verification:

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_rule_diagnostic_freshness.py tests/unit/application/apps/classroom_planner/test_draft_workspace_diagnostics.py tests/unit/web/apps/classroom_planner/test_draft_workspace_api.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_workspace_diagnostics.py -q`
- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers classroomPlannerStateSupport useAnchoredRoomViewportZoom useRoomTouchViewportGestures PlannerPhoneClassroomSeatMap`
- `pdm run fe-gen-api-types`
- `pdm run typecheck`
