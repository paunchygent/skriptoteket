---
type: review
id: REV-PR-0231
title: "Review: PR-0231 + PR-0232 guest Smart parity and local continuity boundary"
status: approved
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
reviewer: "lead-developer"
prs:
  - PR-0231
  - PR-0232
adrs:
  - ADR-0080
links:
  - EPIC-32
  - ST-32-06
  - ADR-0074
  - ADR-0079
  - PR-0223
  - PR-0229
---

## TL;DR

`PR-0231` and `PR-0232` are the two remaining guest-mode bridge slices after
the shipped `PR-0223` public browser-workspace baseline. They must be reviewed
together because they define one boundary: guest parity should include
`Regler`, the expandable Smart settings drawer, solver-based Smart runs, local
undo/redo, and direct-download export, while history-based Smart, `Use history`,
server-owned recovery, and account-owned export/history surfaces remain
authenticated-only.

## Problem Statement

Split implementation is the right delivery shape, but it creates a review risk
if the slices are treated independently.

If `PR-0231` is reviewed alone, guest Smart parity can look complete while
still leaking into authenticated Smart/history seams or implying guest
`Use history`.

If `PR-0232` is reviewed alone, guest local undo/redo and export can drift into
fake durable-history semantics, or guest checkpoint capture can quietly
reintroduce a Smart-history lane that `ADR-0080` explicitly forbids.

The combined review therefore needs to attack the actual fault lines:

- public helper seams vs authenticated owner-scoped APIs
- guest local continuity vs authenticated durable history
- shared planner presentation parity vs guest-specific transport/state wiring
- export/checkpoint continuity vs history-based Smart behavior

## Proposed Solution

Review `PR-0231` and `PR-0232` as one coordinated guest-boundary package.

The reviewer should approve only if the combined package preserves all of the
following:

- guest `Regler` is real and browser-owned
- guest `Grupper` and `Sittplatser` keep the expandable Smart settings drawer
- solver-based Smart runs use explicit public stateless helper seams only
- guest does not expose or simulate `Use history`
- guest undo/redo is local editing state only
- guest export is direct-download only
- guest checkpoint payloads or descriptors do not become guest Smart-history
  inputs
- authenticated export/history/recovery behavior remains unchanged

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0231-st-32-06-guest-regler-workspace-solver-smart-parity-and-expandable-smart-settings-drawer.md` | Guest Smart parity contract and no-history boundary | 8 min |
| `docs/backlog/prs/pr-0232-st-32-06-guest-local-draft-parity-direct-download-export-and-account-only-history-affordance-polish.md` | Local continuity, export, and account-only history contract | 8 min |
| `docs/adr/adr-0080-klassrumskartan-guest-smart-parity-and-history-based-smart-boundary.md` | Frozen Smart/history distinction | 5 min |
| `docs/adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md` | Public helper, browser-owned state, and direct-download export boundary | 5 min |
| `docs/backlog/prs/pr-0223-st-32-06-public-klassrumskartan-demo-capability-matrix-and-browser-workspace-adoption.md` | Shipped public baseline these follow-on slices must not reopen | 5 min |
| `docs/backlog/stories/story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md` | Parent story expectations and parity language | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts` | Guest controller width, rules-mode routing, and transport ownership | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue` | Shared-shell guest parity and blocked account-only affordances | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestControllerSupport.ts` | Guest capability flags and public helper path wiring | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftSession.ts` | Guest Smart state, local undo/redo semantics, and no-op history removal | 8 min |
| `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftWorkspace.ts` | Smart-rule hydration/persistence and guest continuity boundaries | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.vue` | Shared `Regler` presentation reuse | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue` | Grouping Smart drawer, `Use history`, undo/redo, and export affordances | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue` | Seating Smart drawer, `Use history`, undo/redo, and export affordances | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` | Shared planner-shell contract across guest/auth lanes | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue` | Direct-download export vs authenticated recovery/history drift | 4 min |
| `src/skriptoteket/web/api/v1/public_apps_classroom_planner.py` | Public Smart/export helper seams and anonymous-safe transport | 7 min |
| `src/skriptoteket/web/api/v1/apps_classroom_planner.py` | Ensure authenticated seams stay unchanged and are not reused as guest fallback | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts` | Guest overview/rules entry coverage | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` | Guest Smart/export/history parity assertions | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts` | Shared guest/auth shell invariants | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerRulesWorkspacePane.spec.ts` | `Regler` presentation expectations | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.spec.ts` | Export cluster behavior and affordance shape | 3 min |
| `tests/unit/application/apps/classroom_planner/test_smart_rules.py` | Smart-rule state, browser-owned persistence, and no-history semantics | 4 min |
| `tests/unit/application/apps/classroom_planner/test_smart_grouping.py` | Solver-based grouping behavior and guest-safe result ownership | 4 min |
| `tests/unit/application/apps/classroom_planner/test_smart_seating.py` | Solver-based seating behavior and guest-safe result ownership | 4 min |
| `tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py` | Guest local continuity vs authenticated durable-history drift | 4 min |
| `tests/unit/application/apps/classroom_planner/test_grouping_exports.py` | Grouping export boundary and checkpoint semantics | 4 min |
| `tests/unit/application/apps/classroom_planner/test_seating_exports.py` | Seating export boundary and checkpoint semantics | 4 min |
| `tests/unit/web/apps/classroom_planner/test_smart_grouping_api.py` | Public vs authenticated grouping Smart API split | 4 min |
| `tests/unit/web/apps/classroom_planner/test_smart_seating_api.py` | Public vs authenticated seating Smart API split | 4 min |
| `tests/unit/web/apps/classroom_planner/test_grouping_export_api.py` | Guest direct-download grouping export boundary | 4 min |
| `tests/unit/web/apps/classroom_planner/test_seating_export_api.py` | Guest direct-download seating export boundary | 4 min |
| `tests/unit/web/test_public_apps_classroom_planner_imports.py` | Public route import guardrail pattern | 2 min |
| `tests/unit/web/test_apps_classroom_planner_imports.py` | Authenticated route import guardrail stays unchanged | 2 min |
| `scripts/playwright_pr_0223_public_guest_overview_checkpoint2_check.py` | Existing public guest proof lane that should be extended, not forked casually | 4 min |

**Total estimated time:** ~155 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Review `PR-0231` and `PR-0232` as one package | The real risk is the shared guest/auth boundary between them, not the delivery split | [x] |
| Guest parity includes `Regler` and the expandable Smart settings drawer | `ADR-0080` freezes these as part of the same teacher-facing product | [x] |
| Guest parity includes solver-based Smart runs only through explicit public helper seams | Prevents ambient fallback into owner-scoped authenticated APIs | [x] |
| Guest parity excludes history-based Smart and `Use history` | Avoids fake guest history parity and keeps the account-only boundary honest | [x] |
| Guest undo/redo and export checkpoints are local continuity only | Keeps browser-owned editing state separate from authenticated durable history | [x] |
| Guest export is direct-download only with no Vault/job recovery drift | Preserves the public/authenticated export boundary from `ADR-0079` | [x] |
| Authenticated grouping/seating Smart, export, and history flows remain unchanged | Shared-shell reuse must not weaken the logged-in product | [x] |

## Review Checklist

- [x] The combined scope is justified and the two PRs do not duplicate or contradict each other
- [x] Guest `Regler` and Smart-drawer parity are explicit and reviewable
- [x] `Use history` is absent or honestly blocked in guest mode
- [x] Public Smart and export transport stays on dedicated public seams only
- [x] Guest local undo/redo is clearly separated from authenticated durable history
- [x] Guest export checkpoint capture, if retained, is not wired into guest Smart-history behavior
- [x] Shared toolbar/export/smart presentation stays aligned across guest and authenticated routes
- [x] The proof plan covers guest behavior, network boundaries, and unchanged authenticated regression surfaces

## Review Feedback

**Reviewer:** `lead-developer`
**Date:** `2026-04-07`
**Verdict:** `approved`

### Goal Shape To Review Against

The combined package should leave Klassrumskartan with one honest guest story:

1. Guest users can author rules in `Regler`.
2. Guest users can open the same expandable Smart settings drawer shape in
   `Grupper` and `Sittplatser`.
3. Guest users can run solver-based Smart behavior only through explicit public
   helper seams.
4. Guest users cannot access or simulate `Use history`.
5. Guest users can undo/redo locally and export directly, but those capabilities
   do not imply server-owned recovery or history parity.
6. Guest checkpoints, if stored, support browser continuity or later
   authenticated upgrade only.
7. Logged-in Klassrumskartan keeps its existing Smart/history/export behavior.

### Required Verification

- Run:
  - `pdm run fe-test src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerRulesWorkspacePane.spec.ts src/views/apps/components/PlannerExportActionGroup.spec.ts`
  - `pdm run pytest tests/unit/application/apps/classroom_planner tests/unit/web/apps/classroom_planner tests/unit/web/test_public_apps_classroom_planner_imports.py`
  - `pdm run fe-type-check`
  - `pdm run docs-validate`
- Manual checks:
  - guest `Regler`
  - guest grouping Smart settings drawer
  - guest seating Smart settings drawer
  - guest Smart-on grouping run
  - guest Smart-on seating run
  - guest absence or honest blocking of `Use history`
  - guest undo/redo from toolbar and keyboard shortcuts
  - guest direct-download export
  - guest absence of Vault/MyFiles and resumable export-job recovery surfaces
  - unchanged authenticated grouping Smart/history/export flow
  - unchanged authenticated seating Smart/history/export flow
  - network audit showing guest mode uses only explicit public helper seams and
    never falls through to owner-scoped authenticated APIs

### Pass Means

- `PR-0231` and `PR-0232` still read like one coherent boundary instead of two
  competing interpretations
- guest `Regler`, Smart drawer parity, and solver-based Smart runs are real
  without exposing guest `Use history`
- guest local undo/redo and export are real without implying guest durable
  history
- guest checkpoint capture does not become a Smart-history input lane
- authenticated Smart/history/export semantics are not weakened or silently
  rerouted
- proof covers both behavior and transport boundaries strongly enough that the
  reviewer can approve without guessing at hidden rules

### Review Resolution

The split itself is correct and should stay as one retained review package.
`PR-0231` cleanly owns guest Smart parity, and `PR-0232` cleanly owns guest
local continuity/export.

The retained review findings are now resolved.

`PR-0231` now freezes real public solver-backed Smart for both `Grupper` and
`Sittplatser` via dedicated guest routes, and it now requires the
`ADR-0079` abuse-control contract for those helper seams.

`PR-0232` now freezes guest export onto dedicated public direct-download route
families, explicitly forbids fallback into authenticated
`/api/v1/apps/classroom.group-seating-studio/...` export/history/recovery
seams, and publishes the required abuse-control/validation contract for those
routes.

With those tightenings in place, the package is now sharp enough to implement
without inventing missing boundary rules at review time.

### Output

- Verdict: `approved` | `changes_requested` | `rejected`
- If not approved:
  - list the exact boundary leaks or fake-parity seams with file paths
  - state which guest-local-continuity vs authenticated-history assumptions
    were disproven
  - propose `2` to `3` fix directions with pros/cons
- If approved:
  - state explicitly which guest capabilities are real, which remain
    account-only, and which public-helper/browser-owned seams prove that split

### Required Changes

None.

### Suggestions (Optional)

- Keep the eventual implementation review hostile to “close enough” guest
  parity claims. If the guest route cannot do something honestly through the
  public lane, the review should demand explicit omission/blocking instead of
  partial fallback.
- Extend the existing `PR-0223` public guest browser proof lane rather than
  creating a second disconnected guest E2E script unless a new proof surface is
  genuinely required.

### Decision Approvals

- The following policy decisions remain the right direction. Unchecked items
  are now frozen concretely enough in the retained PR docs for implementation.

- [x] The pair should be reviewed as one guest-boundary package
- [x] `Regler` and Smart-drawer parity belong in guest mode
- [x] Solver-based Smart must stay on public helper seams only
- [x] `Use history` must remain account-only
- [x] Guest undo/redo and checkpoint continuity must stay local-only
- [x] Guest export must stay direct-download only
- [x] Authenticated Smart/history/export flows remain unchanged

## Changes Made

1. The retained review now governs `ADR-0080` explicitly through `adrs:` so
   the guest Smart/history boundary is part of the formal review contract
   instead of only a contextual link.
2. The artifact list now names the frozen public-boundary inputs
   (`ADR-0079`, `PR-0223`) and the concrete application/web test files that
   should prove Smart, export, and guest-local-continuity behavior.
3. The retained review is now completed as a re-review approval: the earlier
   `changes_requested` verdict is resolved after tightening the `PR-0231` and
   `PR-0232` planning contracts.
4. The review now records that the planning docs freeze the required public
   Smart/export route families plus the `ADR-0079` abuse-control contract
   strongly enough for implementation to begin.
