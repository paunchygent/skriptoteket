---
type: review
id: REV-PR-0314
title: "Review: PR-0314 solver-owned rule marker semantics"
status: changes_requested
owners: "agents"
created: 2026-05-10
updated: 2026-05-10
reviewer: "codex"
prs:
  - PR-0314
links:
  - ST-27-09
  - ST-29-12
  - ST-29-16
  - ST-29-17
  - PR-0310
  - PR-0313
  - REF-klassrumskartan-solver-rule-diagnostics-contract-2026-05-10
---

## TL;DR

`PR-0314` remains `changes_requested` after second-pass review. The row/bench
`Håll nära` remediation is accepted: direct same-row adjacency is now the clean
solver target and the G20 / SA24D history proof keeps the pair in
`adjacent-row`. Diagnostic freshness is still not fully closed because local
smart-rule mutations can leave old diagnostics in state until the next Smart
run. The bundled `PR-0313` phone pinch lane is improved in code but still needs
actual iPhone confirmation before deploy closeout.

## Problem Statement

This review checks whether `PR-0314` safely moves soft-rule marker truth back to
the solver boundary without replacing a frontend rule engine with stale or
teacher-misaligned backend diagnostics.

## Proposed Solution

The implementation removes local frontend soft-rule fulfillment classification,
adds solver-owned diagnostics for fixed-seat, near-teacher, keep-near, and
keep-apart rules, serializes those diagnostics through authenticated and public
Smart seating responses, and lets the frontend color markers only from matching
diagnostics.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0314-solver-owned-rule-marker-semantics.md` | Scope, acceptance criteria, proof obligations | 10 min |
| `docs/reference/ref-klassrumskartan-solver-rule-diagnostics-contract-2026-05-10.md` | Backend diagnostic vocabulary | 10 min |
| `src/skriptoteket/domain/curated_apps/classroom_planner/smart_rule_diagnostics.py` | Diagnostic truth source | 20 min |
| `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating_scoring.py` | Keep-near scoring semantics | 15 min |
| `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating_candidate_scoring.py` | Candidate tradeoff semantics | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSeatRuleMarkers.ts` | Marker diagnostic matching and coloring | 15 min |
| `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts` | Authenticated diagnostic lifecycle | 10 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftSession.ts` | Public diagnostic lifecycle | 10 min |
| `tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py` | Solver proof semantics | 15 min |
| `tests/unit/domain/curated_apps/classroom_planner/test_smart_rule_diagnostics.py` | Diagnostic proof cases | 15 min |

**Total estimated time:** ~135 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Move soft-rule marker tones from frontend inference to solver diagnostics | Correct boundary for teacher trust | [x] |
| Keep fixed-seat exact-seat marker truth local | Fixed seats are hard direct comparisons | [x] |
| Treat stale diagnostics as usable when student-seat assignments still match | Rule-set edits can still leave unchanged target diagnostics stale | [ ] |
| Treat row/bench same-column `Håll nära` as a valid rotation target | Real use reports this as wrong when same-row adjacency is available | [ ] |
| Treat row/bench same-row adjacency as the only clean two-student target | Second-pass solver proof now matches the teacher-facing requirement | [x] |

## Review Checklist

- [x] Scope is attached to `PR-0314`.
- [x] Solver diagnostics are additive on authenticated and public Smart seating responses.
- [x] Frontend local soft-rule geometry inference is removed.
- [ ] Diagnostic freshness is proven across local rule edits and pending smart-rule changes.
- [x] Row/bench `Håll nära` no-conflict behavior matches the teacher-facing direct-adjacency requirement.
- [ ] Bundled phone-map gesture proof matches real-device behavior before deploy.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-10`
**Verdict:** `changes_requested`

### Required Changes

1. Blocker: stale diagnostics can keep coloring markers after local rule edits.

   Evidence:

   - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSeatRuleMarkers.ts` only checks whether diagnostic `student_ids` still occupy diagnostic `seat_ids`; it does not verify the current rule kind, current rule `student_ids`, smart-rule revision, or whether a local edit is pending.
   - `useClassroomState.ts` and `classroomPlannerGuestDraftSession.ts` store `smartRuleDiagnostics` independently, but smart-rule mutations do not clear or version that state.

   Failure mode:

   Editing an existing relationship rule preserves the rule id. If the seats
   have not changed, an old diagnostic can be reused for the new rule shape,
   rendering markers on the old seats with the new label and old solver tone.

   Required fix:

   Either clear diagnostics on every local seating/rule/template mutation before
   a fresh Smart run, or make diagnostics revisioned and require a full match
   against current rule kind, current rule `student_ids`, and current assignment
   before coloring.

2. Blocker: row/bench `Håll nära` still accepts same-column placement as a valid
   rotation outcome.

   Evidence:

   - `smart_seating_scoring.py` gives row-layout `adjacent-column` a positive
     pair score.
   - `test_smart_seating_solver.py` considers keep-near valid when the pair is
     merely orthogonally adjacent, and the rotation assertion requires both
     `adjacent-row` and `adjacent-column` to appear.
   - Focused verification on 2026-05-10 passed those tests with
     `--override-ini addopts=''`, confirming this is the encoded contract, not
     an accidental untested behavior.

   Failure mode:

   Teachers can ask for `Håll nära` and see the solver place the pair one row
   above/below in the same column even when same-row adjacency should be the
   obvious outcome.

   Required fix:

   Rework the row/bench pair contract so same-row adjacency is the clean
   no-conflict outcome. Same-column placement should be impossible when a
   same-row adjacent pair is available, or should be explicitly degraded and
   only chosen under documented stronger constraints. Update solver scoring,
   diagnostics, and simulation tests together.

3. Blocker: the bundled phone-map pinch lane still fails real-device zoom.

   Evidence:

   - `PR-0313` acceptance requires real two-finger pinch zoom on phone
     `Sittplatser` and `Regler` / `Fast plats`.
   - Real-device testing reported on 2026-05-10 that touch gesture zoom in/out
     still does not work.
   - Current automated proof covers unit/component synthetic paths and Chromium
     CDP touch dispatch, not the failing phone path.

   Required fix:

   Reopen the phone-map gesture lane before deploy-ready closeout. Capture
   proof from the actual phone path, or document a browser-proof path that
   genuinely exercises the same gesture ownership failure mode.

### Suggestions (Optional)

- Add one frontend unit test directly against `buildSeatRuleMarkersBySeatId`
  where a diagnostic exists for rule id `x`, then the current relationship rule
  keeps id `x` but changes kind or student ids. The expected marker tone should
  be neutral until a fresh matching diagnostic exists.
- Add one small no-history solver scenario with one keep-near pair and multiple
  empty adjacent same-row seats. This should assert `adjacent-row` rather than
  only `orthogonally_adjacent`.

### Decision Approvals

- [x] Solver-owned diagnostic boundary
- [x] Fixed-seat local hard-rule truth
- [ ] Diagnostic freshness contract
- [ ] Row/bench keep-near direct-adjacency contract

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0314` | Review moved status from `done` to `blocked`. |
| 2 | `PR-0313` | Real-device pinch failure recorded and status moved from `done` to `blocked`. |

## Remediation Notes

Implemented after the `changes_requested` verdict on 2026-05-10; this review
record remains `changes_requested` until a second-pass review approves the
fixes.

- Diagnostic freshness remediation now clears stored diagnostics on local
  authenticated/guest assignment and template/roster mutations, and marker
  coloring additionally requires the diagnostic to match the current rule id,
  rule kind, current `student_ids`, and current visible assignment.
- Row/bench keep-near remediation now makes same-row `adjacent-row` the only
  no-conflict pair target outside shared-table contexts. Same-column
  `adjacent-column` is still diagnosable as degraded when visible, but the
  solver no longer treats it as the rotation target in the G20 / SA24D history
  proof.
- Phone pinch remediation in `PR-0313` now binds the simplified map's visual
  seat-cell size to the shared zoom state; actual iPhone confirmation is still
  the acceptance proof before deployment closeout.

## Second-Pass Re-review

**Reviewer:** `codex`
**Date:** `2026-05-10`
**Verdict:** `changes_requested`

### Accepted Fixes

- Row/bench `Håll nära` direct-adjacency blocker is closed. The solver now
  scores row/bench `adjacent-row` as the clean pair target, treats
  `adjacent-column` as a tradeoff, and the G20 / SA24D history simulation
  asserts the keep-near pair remains `adjacent-row` across reruns.
- The specific stale-diagnostic case where a reused relationship rule id changes
  kind or student set is covered by current marker matching and focused Vitest
  proof.
- The `PR-0313` code remediation now proves pinch-derived zoom changes the
  rendered phone-seat cell size, not only the hidden zoom percent.

### Remaining Required Changes

1. Blocker: smart-rule mutations still do not clear or version stored solver
   diagnostics.

   Evidence:

   - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts:119`
     through `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSmartRuleActions.ts:292`
     smart-rule mutations call `syncVisibleSessionBindings()` and
     `smartRuleLane.markDirty()`, but receive no diagnostic-clear callback.
   - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts:275`
     through `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStateSupport.ts:278`
     shows `syncVisibleSessionBindings()` only syncs draft and roster lane
     bindings.
   - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSeatRuleMarkers.ts:168`
     through `frontend/apps/skriptoteket/src/views/apps/classroomPlannerSeatRuleMarkers.ts:190`
     still accepts any diagnostic that matches the current target rule shape and
     visible assignment, even when the surrounding smart-rule set is locally
     dirty.

   Required fix:

   Clear stored diagnostics on every local smart-rule mutation before marking
   the smart-rule lane dirty, or carry a solver-input revision through the
   diagnostics and require that revision to match the current smart-rule/draft
   state before marker coloring.

2. Blocker: `PR-0313` still lacks the required real-device iPhone confirmation.

   Evidence:

   - `docs/backlog/prs/pr-0313-shared-phone-classroom-map-real-device-pinch-remediation.md:157`
     through `docs/backlog/prs/pr-0313-shared-phone-classroom-map-real-device-pinch-remediation.md:181`
     explicitly keeps `PR-0313` `in_progress` until actual iPhone confirmation
     is recorded.
   - The focused component proof is useful and now checks rendered cell-size
     changes, but it is still synthetic DOM touch input rather than the failing
     real phone path.

   Required fix:

   Record successful real-device confirmation for phone `Sittplatser` and phone
   `Regler` / `Fast plats`, or attach a browser-proof path that genuinely
   exercises the same WebKit gesture ownership failure mode.

## Third-Pass Remediation Notes

Implemented after the second-pass `changes_requested` verdict on 2026-05-10.
This review record remains `changes_requested` until a new review confirms the
fix and `PR-0313` receives real-device phone proof.

- `classroomPlannerSmartRuleActions.ts` now accepts the shared diagnostic-clear
  callback and calls it for local smart preference, near-teacher,
  relationship-rule, and fixed-seat rule mutations before dirty smart-rule
  state can reuse stale diagnostics.
- `classroomPlannerSmartRuleActions.spec.ts` now proves direct smart-rule
  mutations clear stored diagnostics.
- The near-limit frontend files were split into SRP modules instead of being
  line-shaved:
  `classroomPlannerFixedSeatRuleActions.ts`,
  `classroomPlannerDerivedState.ts`,
  `classroomPlannerGuestDraftHistoryActions.ts`,
  `phoneClassroomSeatMapLayout.ts`, and
  `useClassroomPlannerRuleDiagnostics.ts`.

### Second-Pass Verification

- `pdm run fe-test -- --run classroomPlannerSeatRuleMarkers PlannerPhoneClassroomSeatMap useRoomTouchViewportGestures`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_near_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -m simulation --override-ini addopts='' -q`
