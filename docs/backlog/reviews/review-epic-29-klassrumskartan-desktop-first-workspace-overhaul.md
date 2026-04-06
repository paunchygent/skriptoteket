---
type: review
id: REV-EPIC-29
title: "Review: Klassrumskartan desktop-first workspace overhaul"
status: changes_requested
owners: "agents"
created: 2026-03-28
updated: 2026-04-06
reviewer: "lead-developer"
epic: EPIC-29
adrs:
  - ADR-0069
  - ADR-0071
  - ADR-0072
stories:
  - ST-29-01
  - ST-29-02
  - ST-29-03
  - ST-29-04
  - ST-29-05
  - ST-29-06
  - ST-29-07
---

## TL;DR

EPIC-29 proposes a dedicated redesign lane for Klassrumskartan now that the planner logic is
largely in place. The package keeps core planner contracts stable while overhauling the interface
as a desktop-first, symbol-led, workspace-heavy product: shared control primitives first, shell
compression second, then overview/grouping/seating/rules composition, and only after that a reduced
mobile companion layout.

## Problem Statement

Klassrumskartan has reached the point where presentation quality is the main product risk. The
planner works, but the current interface still spends too much visual budget on stacked bands,
card-equal sections, and text-heavy controls. Existing nearby polish stories help, but they do not
yet form a coherent redesign framework or a clear desktop-first end-state.

## Proposed Solution

Create a new dedicated redesign epic instead of stretching EPIC-26 export/import work or EPIC-27
smart-assignment work beyond their reviewed scope. Start with canonical symbols and shared control
primitives, then compress the shell and stabilize shared desktop workspace composition, then
redesign overview/grouping/seating/rules in order, and only then define reduced mobile companion
layouts. Use the new workspace doctrine as the planning reference throughout.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md` | Target end-state and desktop-first doctrine | 6 min |
| `docs/backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md` | Scope and sequencing | 8 min |
| `docs/backlog/stories/story-29-01-klassrumskartan-canonical-operation-symbols-and-planner-control-primitives.md` | Shared symbols and control system | 5 min |
| `docs/backlog/stories/story-29-02-klassrumskartan-workspace-shell-compression-and-low-value-feedback-band-reduction.md` | Shell compression and feedback model | 5 min |
| `docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md` | Shared desktop layout primitives | 5 min |
| `docs/backlog/stories/story-29-04-klassrumskartan-overview-hierarchy-and-class-first-dashboard-redesign.md` | Overview hierarchy | 4 min |
| `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md` | Grouping and seating composition | 5 min |
| `docs/backlog/stories/story-29-06-klassrumskartan-rules-workspace-rail-map-inspector-rebalance.md` | Rules workspace hierarchy | 4 min |
| `docs/backlog/stories/story-29-07-klassrumskartan-reduced-mobile-companion-layouts-and-breakpoint-cutover.md` | Mobile companion scope and breakpoint policy | 4 min |

**Total estimated time:** ~46 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| New epic instead of extending EPIC-26 or EPIC-27 | Export/import and smart-assignment are active but narrower lanes; the redesign needs its own outcome and review surface | [ ] |
| Desktop-first is the canonical product stance | Prevent desktop workspaces from collapsing into mobile-first stacked compromises | [ ] |
| Symbol system ships before layout restyling | Shared operation language must stabilize before workspace-specific redesign begins | [ ] |
| Shared primitives ship before workspace-specific slices | Later stories should build on common shell/zoning/scroll/control seams | [ ] |
| Reduced mobile companion layouts ship last | Smaller-screen behavior should adapt from the settled desktop product, not shape it prematurely | [ ] |

## Review Checklist

- [x] ADRs still provide sufficient product/contract boundaries
- [x] EPIC scope is appropriate
- [ ] Stories have testable acceptance criteria
- [ ] Sequencing reduces redesign risk instead of front-loading visual churn
- [ ] Risks and overlaps with existing EPIC-26 stories are identified clearly

## Review Feedback

**Reviewer:** @lead-developer
**Date:** 2026-03-28
**Verdict:** changes_requested

### Required Changes

1. Resolve the EPIC-26 overlap explicitly before approval. `ST-26-06`, `ST-26-07`, and
   `ST-26-08` cannot remain as a parallel ready polish lane while `ST-29-03` and `ST-29-04`
   absorb the same desktop composition and hierarchy work. Update EPIC-26 / EPIC-29 so it is
   clear whether those stories are prerequisites, folded in, or superseded.
2. Define a canonical viewport-proof matrix for the redesign. The doctrine/epic should name the
   exact breakpoint tokens or viewport widths used for `phone`, `tablet`, `laptop`, and
   `desktop` proof so the repeated "canonical desktop widths" / "common laptop widths" acceptance
   criteria become reviewable instead of interpretive.
3. Move the accessibility/discoverability requirement in `ST-29-01` into acceptance criteria.
   Icon-first controls are the right direction, but tooltip/label/aria expectations cannot live
   only in notes if this story is meant to lock the shared control contract.
4. Align the sequencing contract for `Regler`. `ST-29-06` should either depend on `ST-29-03` or
   explicitly explain why the rules workspace is allowed to bypass the shared desktop-composition
   primitives even though the epic says workspace-specific slices build on them.

### Suggestions (Optional)

- If `ST-26-06`, `ST-26-07`, and `ST-26-08` are folded into EPIC-29, preserve their sharper
  desktop-proof language so the redesign stories inherit concrete usability checks instead of only
  aesthetic direction.

### Decision Approvals

- [x] New epic instead of extending EPIC-26 or EPIC-27
- [x] Desktop-first as the canonical product stance
- [x] Symbol system before layout restyling
- [ ] Shared primitives before workspace-specific slices
- [x] Reduced mobile companion layouts last

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `EPIC-29` | Drafted a dedicated redesign epic aligned to the new workspace doctrine |
| 2 | `ST-29-01`..`ST-29-07` | Added a paced story stack from shared symbols/primitives into workspace-specific redesign and responsive cutover |
| 3 | `REV-EPIC-29` | Created the required review surface before any implementation begins |
| 4 | `EPIC-26`, `EPIC-29`, `PR-0127`..`PR-0132`, `ST-29-03`, `ST-29-04` | Resolved overlap by moving redesign execution ownership into `EPIC-29`, reparenting the applicable task slices into the new story stack, and removing the conflicting EPIC-26 story docs |
| 5 | `EPIC-29`, `REF-klassrumskartan-workspace-ui-doctrine-2026-03-28`, `ST-29-02`..`ST-29-07` | Added an explicit `phone` / `tablet` / `laptop` / `desktop` viewport-proof matrix and updated acceptance criteria to reference the named review viewports |
| 6 | `ST-29-01` | Moved icon accessibility and discoverability requirements into acceptance criteria so the symbol-system slice locks both space efficiency and usability |
| 7 | `ST-29-06` | Added `ST-29-03` as an explicit dependency so the rules workspace cannot bypass shared desktop-composition primitives |

## Supplemental Review Record: PR-0226 Shared Planner Shell Parity and Grouping Viewport-Height Stabilization

**Reviewer:** `lead-developer`
**Date:** 2026-04-06
**Verdict:** `approved`

### Scope To Review

- `docs/backlog/prs/pr-0226-st-29-11-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md`
- `docs/backlog/stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md`
- `docs/backlog/epics/epic-29-klassrumskartan-desktop-first-workspace-overhaul.md`

### Required Review Outputs

1. Confirm the slice really belongs under `ST-29-11` shared primitive/parity tightening rather
   than reopening core workspace redesign scope.
2. Confirm sticky toolbar behavior is specified as one shared viewport-relative shell contract,
   not as a guest-only patch or a page-height/wrapper-dependent offset.
3. Confirm the grouping-height stabilization contract is bounded and reviewable:
   - grouping board lane floor is explicitly frozen at `480px`
   - unassigned-student pool floor is explicitly frozen at `480px`
   - both floors are tied to the current seating `RoomCanvas` viewport baseline
   - no content-count collapse is allowed when only a few groups exist
4. Confirm the proposed taller group buckets are frozen as explicit `56px` assigned-row floors
   and `112px` empty drop-target floors, and that the proof plan requires direct component/spec
   assertions for those values instead of shell-only or screenshot-only evidence.
5. Approve or reject whether `PR-0226` may proceed as the next implementation slice.

### Review Resolution

The previously requested review tightening is resolved. `PR-0226` now freezes the
shared `480px` grouping-floor contract, the `56px` / `112px` group-card floors,
and the fresh grouping-draft seed count at `4`, with focused component/spec and
draft-lifecycle proof added before implementation close-out.

### Suggestions (Optional)

- Keep the current shared-shell framing. The guest/authenticated sticky-toolbar drift is a valid
  `ST-29-11` follow-up because the bug is still wrapper/parity hardening, not a new workflow
  redesign. The grouping-height portion just needs a tighter review contract so it stays a bounded
  stabilization slice.

### Decision Approvals

- [x] `PR-0226` is the right bounded follow-up slice for the reported guest/authenticated shell
      parity drift.
- [x] The sticky toolbar contract should be shared and viewport-relative across guest and
      authenticated shells.
- [x] Grouping should keep a shared explicit `480px` minimum-height floor for both the board lane
      and student-pool lane instead of shrinking to current content.
- [x] Group cards and empty drop targets should use the explicit `56px` / `112px` minimum-height
      floors and prove them through focused component/spec assertions.
- [x] `PR-0226` may proceed to implementation once this supplemental review clears.

### Reviewer Notes

- This supplemental review task was added after `PR-0226` was created so the follow-up slice has a
  retained review gate inside the canonical `REV-EPIC-29` record.

### Changes Made

1. `PR-0226` now freezes the grouping-height contract against the current seating baseline:
   `480px` for both the grouping board lane and the unassigned-student pool.
2. `PR-0226` now freezes the taller group-bucket contract as explicit `56px` assigned-row floors
   and `112px` empty drop-target floors instead of the earlier "about 25 percent taller"
   phrasing.
3. `PR-0226` now requires focused component/spec proof through `GroupCard.spec.ts`,
   `GroupBoard.spec.ts`, and `PlannerGroupingWorkspacePane.smart-rules.spec.ts` in addition to the
   guest/authenticated shell parity checks.
4. `PR-0226` now also freezes fresh grouping drafts to `4` default groups in both guest and
   authenticated mode so the parity contract includes blank-draft seeding behavior.

## Supplemental Review Record: PR-0227 Exact Two-Row Grouping Board Height Contract at Desktop Baseline

**Reviewer:** `lead-developer`
**Date:** 2026-04-06
**Verdict:** `approved`

### Scope To Review

- `docs/backlog/prs/pr-0227-st-29-11-exact-two-row-grouping-board-height-contract-at-desktop-baseline.md`
- `docs/backlog/stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md`
- `.agents/handoff.md`

### Required Review Outputs

1. Confirm `PR-0227` stays a bounded `ST-29-11` desktop-first hardening slice rather than
   reopening the broader responsive/mobile workflow redesign.
2. Confirm the contract distinguishes the empty/default exact `480px` desktop proof case from the
   populated-card behavior after students are assigned.
3. Confirm the `234px` group-card rule is expressed as a desktop `min-height` floor, not a
   universal hard cap that would force clipping or internal scrolling for populated cards.
4. Confirm smaller breakpoints are explicitly allowed to diverge from the desktop-heavy workspace
   behavior and are not silently locked to the desktop proof math.
5. Confirm the proof plan now requires a browser-level rendered measurement for the exact
   `480px` empty/default board case in addition to class/token assertions.

### Review Resolution

The previously requested tightening is resolved. `PR-0227` now freezes a desktop-only group-card
floor where `234px` persists as the desktop `min-height` after assignment, while the exact
`480px` math is retained only for the empty/default 4-card desktop proof case. The task also now
states that populated cards may grow past the floor without forced internal scrolling and that
smaller breakpoints may intentionally diverge from the desktop workspace behavior.

### Decision Approvals

- [x] `PR-0227` remains a valid bounded `ST-29-11` follow-up for desktop-first grouping hardening.
- [x] The exact `480px` rule is now correctly limited to the empty/default 4-card desktop proof
      case.
- [x] The `234px` desktop card rule is now correctly frozen as a `min-height` floor that persists
      after assignment rather than as a universal maximum.
- [x] Populated cards are explicitly allowed to grow beyond the floor without mandatory internal
      scrolling in this slice.
- [x] Smaller breakpoint workflows are explicitly allowed to diverge from the desktop proof path.
- [x] The proof plan now requires rendered browser measurement for the exact empty/default
      `480px` contract.

### Changes Made

1. `PR-0227` acceptance criteria now distinguish:
   - the exact empty/default desktop `480px` board proof
   - the persistent desktop `234px` card `min-height` floor after assignment
2. `PR-0227` now explicitly states that populated cards may grow beyond `234px` and must not be
   forced into clipping or mandatory internal scrolling in this slice.
3. `PR-0227` now explicitly limits the contract to the desktop proof path and allows smaller
   breakpoint workflows to diverge intentionally.
4. `PR-0227` now requires browser geometry proof via `getBoundingClientRect()` with an explicit
   `0.5px` tolerance for the empty/default `480px` verification step.

## Supplemental Review Task: PR-0228 Planner Workspace Shell, Breakpoint, and Overflow Contract

**Reviewer:** `lead-developer`
**Date:** `2026-04-06`
**Verdict:** `changes_requested`

### Role

You are the fresh-eyes post-implementation reviewer for the current `PR-0228` planner workspace
regression lane.

### Scope

- In scope:
  - `PR-0228`
  - the shared planner workspace shell and pane contract across guest and authenticated routes
  - breakpoint behavior at `laptop` and `desktop`, plus the currently failing resize / in-between
    viewport behavior
  - toolbar, student-pool rail, grouping board, and seating canvas overflow ownership
- Out of scope:
  - backend planner logic, grouping math from `PR-0226` / `PR-0227`, and broader mobile workflow
    redesign unless the review proves the current shared shell contract is invalidated by them

### Mandatory Repomix Package (External Review)

- Package: `.agents/repomix_packages/repomix-pr-0228-workspace-contract-review.xml`
- Template: `code-review`
- Included files: `27`
- Current largest files by token count:
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`
  - `scripts/playwright_pr_0227_group_board_height_contract_check.py`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`

### Goal Shape To Review Against

At the named `laptop` and `desktop` review widths, Klassrumskartan should behave like a bounded
workspace frame rather than ordinary page content:

1. Page header, planner top panel, and toolbar remain stable chrome above the active workspace.
2. The active workspace body becomes one bounded region that owns the visible grouping/seating
   work area.
3. Inside that region, the student-pool rail is a stable side lane with a fixed visible header and
   a scrolling list body.
4. The active right-hand lane owns the deeper grouping-board or seating-canvas scrolling.
5. The toolbar and workspace body must not disappear, collapse, or change overflow behavior merely
   because the browser crosses a breakpoint or is resized through an intermediate width band.
6. Smaller breakpoints may intentionally diverge from the desktop-heavy workspace model, but the
   cutover must be explicit and stable rather than accidental or shell-fragile.

### Desired Implementation Direction To Test Critically

The most likely robust direction is a shared shell contract where:

- the planner shell owns the height budget and breakpoint cutover
- the workspace body has one clear overflow owner instead of nested competing scrollers
- the student-pool rail keeps only local header/list scrolling responsibilities
- the right-hand board/canvas lane owns deeper work-area scroll
- CSS layout primitives (`min-h-0`, bounded rows, explicit split-lane ownership) carry the
  contract first, with runtime measurement allowed only if the reviewer can justify why CSS alone
  cannot provide a stable contract

Treat that as a design direction to evaluate, not as an approved implementation.

### Do Not Assume

- Do not assume the issue is a backend failure; current container evidence shows planner workspace
  endpoints returning `200`.
- Do not assume the current `window.innerHeight` / `ResizeObserver` pane-budget logic is either the
  root cause or the correct fix.
- Do not assume the problem is only “sticky rail lost again”; the bug may sit in shared shell
  height ownership, breakpoint cutover, overflow ownership, resize transitions, or a combination.
- Do not assume the `desktop` split-workspace behavior should be copied unchanged to all smaller
  breakpoints.
- Do not assume the present `xl:` cutover is the right breakpoint boundary; verify against the
  named review widths and the failing in-between width band.

### Artifacts To Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0228-st-29-11-follow-up-desktop-student-pool-rail-stickiness-restoration.md` | Current intended contract and frozen decisions | 5 min |
| `docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md` | Canonical shared desktop-composition ownership | 4 min |
| `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md` | Shipped grouping/seating composition expectations | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue` | Planner route shell height/frame ownership | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` | Shared authenticated planner shell | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue` | Guest shell parity | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceModeSurface.vue` | Shared pane shell and current measured-height seam | 6 min |
| `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts` | Breakpoint and overflow contract tokens | 5 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue` | Grouping lane composition | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue` | Seating lane composition | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue` | Rail header/list scroll behavior | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue` | Board-lane interaction with overflow ownership | 3 min |
| `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue` | Seating canvas overflow expectations | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts` | Grouping layout regression coverage | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts` | Seating layout regression coverage | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts` | Shared shell assertions | 4 min |
| `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` | Guest shared-shell assertions | 4 min |
| `scripts/playwright_pr_0227_group_board_height_contract_check.py` | Current live proof lane and its blind spots | 5 min |

**Total estimated time:** ~76 minutes

### Review Checklist

- [ ] The review identifies the true height and overflow owners at each planner-shell layer.
- [ ] The breakpoint contract is explicit for `laptop`, `desktop`, and the currently failing
      in-between resize band.
- [ ] The recommended fix removes brittle nesting assumptions rather than layering new sticky or
      measured-height patches on top.
- [ ] Guest and authenticated shells are evaluated as one shared contract, not as isolated bugs.
- [ ] Toolbar overflow behavior is reviewed together with pane-body rendering rather than as a
      disconnected issue.
- [ ] The regression-proof plan includes both static specs and live browser checks at the failing
      widths.

### Required Verification

- Run:
  - `pdm run fe-test src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run python -m scripts.playwright_pr_0227_group_board_height_contract_check --base-url http://127.0.0.1:5173`
- Manual checks:
  - authenticated `Grupper` and `Sittplatser`
  - guest `Grupper` and `Sittplatser`
  - full desktop viewport
  - failing intermediate width / resize transition
- Pass means:
  - the workspace body remains visible and structurally intact below the toolbar
  - the student-pool rail and right-hand lane preserve their intended relationship at desktop/laptop
  - toolbar overflow remains orderly
  - no shell-specific divergence appears between guest and authenticated routes

### Output

- Verdict: `approved` | `changes_requested` | `rejected`
- If not approved:
  - list the exact structural fault lines with file paths
  - state which assumptions were disproven
  - propose `2` to `3` fix directions with pros/cons
- If approved:
  - state the target shell/breakpoint/overflow contract clearly enough that implementation can
    proceed without inferring unstated layout rules

### Close-out (Required If Approved)

- Update this retained review record with the final verdict and decision approvals.
- Update `PR-0228` status and notes to reflect the approved structural direction.
- Update `.agents/handoff.md` with the review outcome and verification commands.
- Run `pdm run docs-validate` and record the result.

### Review Resolution

`PR-0228` is not ready to approve. The current implementation improves the local student-pool
header/list contract, but it does not yet establish one bounded planner workspace body that owns
desktop/laptop height and overflow.

Live review against the real authenticated `SA24D` / `G20` drafts on `http://127.0.0.1:5173`
showed the new pane shell still overflowing `main.auth-main-content` on both named proof
viewports:

- `Grupper` at `desktop` (`1440x900`): pane shell height = `480px`, but authenticated main still
  overflowed (`clientHeight=843`, `scrollHeight=928`)
- `Grupper` at `laptop` (`1366x768`): pane shell height = `480px`, but authenticated main still
  overflowed (`clientHeight=711`, `scrollHeight=928`)
- `Sittplatser` at `desktop` (`1440x900`): pane shell height = `480px`, while the right-hand lane
  also kept its own scroll (`lane scrollHeight=731`, `clientHeight=480`) and authenticated main
  still overflowed (`clientHeight=843`, `scrollHeight=928`)
- `Sittplatser` at `laptop` (`1366x768`): pane shell height = `480px`, lane scroll remained local
  (`scrollHeight=678`, `clientHeight=480`), and authenticated main still overflowed
  (`clientHeight=711`, `scrollHeight=928`)

At `1279px` width the split workspace dropped into a long stacked column (`Grupper` pane shell
`1330px`, `Sittplatser` pane shell `909px`) without an explicit approved breakpoint contract or a
review proof that the resize transition is the intended cutover.

### Structural Fault Lines

1. `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceModeSurface.vue`
   (`syncDesktopPaneHeight`) now clamps the pane shell to `Math.max(480, window.innerHeight -
   rect.top)`. On the real `SA24D` / `G20` planner route the visible space below the toolbar is
   already smaller than `480px` at both named proof heights, so the clamp guarantees outer
   authenticated-page overflow instead of removing it.
2. `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts` plus
   `frontend/apps/skriptoteket/src/components/layout/AuthLayout.vue` still leave multiple vertical
   overflow owners in play. The authenticated shell keeps `overflow-y: auto`, the pane shell also
   uses `overflow-y: auto`, and the right-hand workspace lane can scroll internally too. That is
   not the one clear overflow owner this review requested.
3. `scripts/playwright_pr_0227_group_board_height_contract_check.py` does not prove the new shell
   seam. The newly added `_assert_pool_stays_sticky_during_workspace_scroll(...)` helper is never
   called, and the script does not assert the `1279px` resize/cutover band that this review asked
   to validate.
4. The focused specs in
   `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`,
   `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`,
   `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts`,
   and
   `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
   still only prove class-token presence. They do not prove rendered geometry, outer-shell
   overflow elimination, or the failing resize transition.

### Disproven Assumptions

- The measured pane shell does **not** currently own the desktop/laptop height budget; the
  authenticated page shell still scrolls on the named proof widths.
- The current `window.innerHeight` / `ResizeObserver` seam is **not** a sufficient fix by itself.
  It preserves a `480px` pane even when the actual remaining viewport budget is materially smaller.
- The existing proof lane does **not** validate the true shared scroll-owner contract or the
  in-between resize band.
- Guest/authenticated parity is still mostly a shared-component inference plus token-level spec
  coverage, not a retained live proof of the reviewed shell contract.

### Fix Directions

1. Move height budgeting up to the planner route shell and keep the pane shell CSS-first.
   Pros: lets one outer planner workspace own the visible budget, removes the need for the pane
   shell to outgrow the remaining viewport, and aligns with the review’s “CSS first” direction.
   Cons: likely requires rebalancing `ClassroomPlannerView.vue`, `PlannerWorkspaceShell.vue`, and
   the authenticated/guest shell wrappers together instead of patching one component.
2. If runtime measurement must stay, cap the pane shell to the real available budget and keep the
   `480px` rules as inner-lane `min-height` floors only.
   Pros: smallest conceptual delta from the current patch and preserves the accepted grouping/seating
   floor language.
   Cons: still leaves a runtime-coupled seam and remains more fragile than a pure flex/grid budget.
3. Tighten the proof plan before another implementation pass.
   Pros: the next attempt can fail fast if `main.auth-main-content`, the pane shell, or the
   document starts owning scroll unexpectedly, and it can explicitly cover `1440`, `1366`, and the
   sub-`xl` resize band.
   Cons: requires updating both the targeted Playwright lane and at least one browser-level layout
   proof around real geometry rather than class tokens alone.

### Decision Approvals

- [x] `PR-0228` remains a valid bounded `ST-29-11` follow-up rather than a full workspace-redesign
      restart.
- [ ] The current measured pane-shell implementation is acceptable as the shared shell contract.
- [ ] The current breakpoint/cutover contract is explicit enough to approve.
- [ ] The current regression-proof plan is sufficient to guard the reviewed shell/overflow contract.
