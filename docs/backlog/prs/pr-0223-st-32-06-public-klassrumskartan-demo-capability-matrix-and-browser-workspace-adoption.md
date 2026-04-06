---
type: pr
id: PR-0223
title: "ST-32-06: public Klassrumskartan demo capability matrix and browser-workspace adoption"
status: in_progress
owners: "agents"
created: 2026-04-05
updated: 2026-04-06
stories:
  - "ST-32-06"
tags: ["frontend", "backend", "klassrumskartan", "public-access", "guest-workspace"]
dependencies:
  - "ADR-0079"
  - "ST-32-04"
  - "ST-32-05"
  - "EPIC-27"
  - "EPIC-29"
acceptance_criteria:
  - "Given Klassrumskartan becomes the first concrete public browser-workspace consumer, when this slice is specified and implemented, then guest-allowed, guest-altered, and guest-blocked behavior is explicit across rosters, templates, smart rules, drafts, history, smart runs, import preview, export, reset, and authenticated-only affordances."
  - "Given the public Klassrumskartan demo is browser-owned, when guest users create or edit rosters, templates, smart rules, or drafts, then those changes persist only in the browser workspace and are not re-homed into account-owned APIs before an explicit authenticated upgrade later occurs."
  - "Given guest Klassrumskartan still needs parser- or compute-assisted flows, when import preview or smart compute runs, then the public helper namespace remains stateless and durable guest continuity stays browser-owned."
  - "Given guest export is available, when a guest user exports, then the result is delivered as an immediate direct download without Vault/MyFiles recovery or resumable account-owned job surfaces."
  - "Given a guest user later authenticates, when the first authenticated visit to Klassrumskartan detects pending guest work, then the existing authenticated upgrade prompt from ST-32-05 appears; and generic login/registration flows outside the app do not trigger migration behavior."
  - "Given the guest demo includes a reset affordance, when the user clears the workspace, then the action is labeled `Kasta`, uses plain-language browser/shared-device confirmation copy, and removes browser-owned guest state without implying account-side deletion."
  - "Given guest mode is the same teacher tool rather than a separate demo product, when the public browser-owned workspace renders, then it keeps the same Klassrumskartan layout and visual language as the authenticated app while account-owned affordances stay minimally disabled/signposted via subtle lock states, short tooltips, and one small plain-language system message."
---

## Problem

`ST-32-04` and `ST-32-05` already established the browser-owned snapshot
contract and authenticated upgrade boundary. What remains for the unfinished
part of this PR is not the overall direction, but a small set of still-unfrozen
guest-mode details that need one explicit contract inside this PR so the
implementation does not drift.

## Current implementation status

As of 2026-04-06, checkpoints 1-3 are implemented locally and checkpoint 4
remains pending.

Implemented so far:

- the public Klassrumskartan route no longer renders the old placeholder/stub;
  it now renders the real overview shell
- public overview state is bootstrapped from the browser-owned guest snapshot
  seam through a dedicated guest overview controller/view
- browser-owned roster/template authoring is now wired through the same public
  overview shell:
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts`
    now owns guest bootstrap/selection orchestration
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestOverviewCrud.ts`
    now owns public overview modal + delete-confirmation CRUD
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestControllerSupport.ts`
    now owns snapshot hydration/normalization helpers
  - the old
    `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestOverviewShell.ts`
    controller has been removed
- guest roster/template create, edit, delete, and selection all persist back
  into the browser-owned guest snapshot lane
- guest roster import preview now stays on the dedicated public/stateless seam
  only:
  - `/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview`
- authenticated Klassrumskartan orchestration remains separate and unchanged
- checkpoint 3 guest planner continuity is now in place:
  - the public shell swaps between overview and a dedicated guest planner shell
    through `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestOverviewView.vue`
    and `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue`
  - guest planner state is browser-owned and split across focused modules:
    `useClassroomPlannerGuestController.ts`,
    `classroomPlannerGuestDraftSession.ts`,
    `classroomPlannerGuestDraftPersistence.ts`,
    `classroomPlannerGuestDraftWorkspace.ts`, and
    `classroomPlannerGuestDraftMutations.ts`
  - guest `Grupper` / `Sittplatser` now reopen from the same browser snapshot,
    survive overview round-trips, preserve the selected overview classroom
    across planner mode switches, and no longer let the shell selector drift
    away from the hydrated draft kind
- checkpoint-1 public presentation uses final-state user copy only:
  - the locked guest system message is shown
  - temporary implementation-stage helper/tooltips are not shown
  - unfinished public modes/actions are hidden rather than explained with
    temporary copy

Not implemented yet:

- later follow-on work:
  - guest smart rules
  - guest export and export-backed checkpoint UX
  - final account-only affordance behavior by surface

Local proof so far:

- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/PublicAppHostView.spec.ts`
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/PublicAppHostView.spec.ts src/views/apps/components/CreateRosterModal.spec.ts src/views/apps/components/CreateRoomTemplateModal.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_pr_0223_public_guest_overview_checkpoint2_check --base-url http://127.0.0.1:5173`
- live browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`:
  - public route renders the real overview shell with the final registration
    system message still intact
  - guest can create, edit, and delete a roster in the browser-owned workspace
    while import preview uses the public helper seam
  - guest can create, edit, and delete a room template in the browser-owned
    workspace
  - no owner-scoped authenticated planner/catalog/draft/export API seam was
    used; the network audit observed only `GET /api/v1/auth/me`,
    `GET /api/v1/public/apps/classroom.group-seating-studio`, and
    `POST /api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview`
  - checkpoint-3 continuity is now live too:
    - overview-selected classroom keeps `Sittplatser` enabled after entering
      `Grupper`
    - `Sittplatser -> Grupper` returns to the real grouping lane instead of
      leaving the shell stuck on seating
    - artifacts: `.artifacts/pr-0223-public-guest-checkpoint3/`

Reviewer follow-up retained for this checkpoint:

- keep a focused test that the public empty state preserves the final-state
  registration copy while unfinished guest actions stay hidden
- when this slice is re-verified live, keep browser/network evidence that the
  guest overview does not hit owner-scoped authenticated APIs

## Checkpoint-3 implementation freeze (2026-04-06)

Checkpoint 3 is now explicitly the next bounded implementation slice inside
`PR-0223`. It must stop after guest grouping/seating draft continuity lands.

### Scope in

- extend
  `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts`
  beyond overview-only orchestration so the public shell can open and resume
  guest `Grupper` / `Sittplatser`
- keep browser-owned draft/session logic in new focused guest modules rather
  than growing the existing checkpoint-2 files further
- reuse the existing presentation shell where it stays transport-agnostic:
  `PlannerClassWorkspace.vue`, `PlannerWorkspaceShell.vue`, and their child
  panes/toolbars
- keep draft continuity browser-owned through the existing guest snapshot
  contract in
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshot.ts`
  and
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshotMapping.ts`
- update the targeted existing Playwright proof in
  `scripts/playwright_pr_0223_public_guest_overview_checkpoint2_check.py`
  rather than creating a second overlapping PR-0223 browser script

### Scope out

- guest smart-rule authoring and persistence
- guest direct-download export behavior and checkpoint UX polish
- public smart-run compute seams
- any reuse of authenticated `/api/v1/apps/classroom.group-seating-studio/...`
  draft, history, export, or smart-run endpoints
- any broadening of
  `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerRouteShell.ts`
  into a dual-mode guest/authenticated controller

### Planned module split

The checkpoint-3 code shape should stay below the repo file-size ceiling by
adding focused guest draft/session modules instead of inflating the
checkpoint-2 files.

- new module:
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftSession.ts`
  - own guest draft open/resume/return transitions, public planner-screen
    state, and screen-specific snapshot hydration
- new module:
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftMutations.ts`
  - own pure browser-owned snapshot mutations for grouping/seating drafts and
    related UI state updates
- existing module touched:
  `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts`
  - orchestrate the new helpers and expose one broader guest workspace surface
- existing module touched:
  `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestOverviewView.vue`
  - re-enable only the guest-capable `Grupper` / `Sittplatser` entry points
- existing checkpoint-2 helper files
  `classroomPlannerGuestControllerSupport.ts` and
  `classroomPlannerGuestOverviewCrud.ts`
  - keep their current responsibilities and do not absorb guest planner-session
    orchestration

## Already locked decisions

These are already decided and must not be reopened in this PR:

- guest mode keeps the same Klassrumskartan layout and visual language as the
  authenticated app
- rosters, templates, smart rules, and drafts are fully authorable in the
  browser-owned guest workspace
- import preview and smart compute may stay stateless/server-assisted only
- guest export is direct-download only
- guest-local history means local draft continuity plus export-backed
  checkpoints only; authenticated recovery/history remains account-owned
- upgrade prompting happens only on the first authenticated Klassrumskartan
  visit
- the guest reset/discard label is `Kasta`
- account-owned features should be minimally disabled/signposted rather than
  replaced by a separate guest UI
- guest mode must never fall through to owner-scoped authenticated APIs when a
  dedicated public helper seam is absent; the capability stays blocked instead

## Open decisions to freeze in this PR

Only the following details remained to be frozen here. They are now locked and
must be implemented exactly as written below.

### 1. Guest-limit system message

Locked decision:
- one small system message at the top of the guest workspace shell
- exact copy: `Vissa funktioner kräver att du registrerar ett konto. Tryck här för att skapa ett.`
- only the word `här` is linked to the registration route
- do not repeat this message in multiple cards, drawers, or workspaces

### 2. Account-only affordance policy by surface

Locked decision:
- each account-owned affordance must be assigned one of:
  - `disabled + tooltip`
  - `not rendered in guest mode`
- default to `disabled + tooltip` only when the visible control helps the user
  understand a nearby missing capability without creating a dead-end
- use `not rendered in guest mode` for recovery/job/Vault/history surfaces and
  other secondary affordances that would otherwise imply account-owned
  continuity the guest workspace does not have
- do not use a third `hidden` state in this contract; this PR freezes the
  user-visible behavior, not CSS-only implementation detail

### 3. Guest export entry and blocked recovery behavior

Locked decision:
- keep the same visible export entry point where possible
- guest export starts immediate download directly from that surface
- job recovery, Vault/MyFiles, and resumable export surfaces are `not rendered
  in guest mode`
- guest mode must not render pseudo-working dead-end recovery surfaces

## Capability matrix by surface

This PR must freeze the guest/account boundary explicitly for:

- `Översikt`
- `Grupper`
- `Sittplatser`
- `Regler`
- import preview
- smart runs
- local draft continuity and export-backed checkpoints
- export surfaces
- authenticated-only recovery/history/job affordances

For each surface, the matrix should state:

- what is fully available in guest mode
- what is browser-owned and later importable
- what is account-only and how it is shown:
  - `disabled + tooltip`
  - `not rendered in guest mode`

### Frozen surface policy

The following surface-level decisions are now locked for implementation.

#### Översikt

- guest-allowed:
  - create, edit, delete, and select rosters
  - create, edit, delete, and select templates
- browser-owned:
  - roster and template changes
  - selected roster/template UI state
- account-only:
  - none on the core overview authoring controls

#### Grupper

- guest-allowed:
  - create or resume a grouping draft
  - shuffle, manual placement, group count changes, and local smart-rule-aware drafting
- browser-owned:
  - active grouping draft and associated UI state
- account-only:
  - authenticated history/recovery surfaces beyond the local draft lane:
    - `not rendered in guest mode`
  - any shared shell control that explains a missing account-owned history or
    recovery capability:
    - `disabled + tooltip`

#### Sittplatser

- guest-allowed:
  - create or resume a seating draft
  - manual placement, shuffle, template switching, and local smart-rule-aware drafting
- browser-owned:
  - active seating draft and associated UI state
- account-only:
  - authenticated history/recovery surfaces beyond the local draft lane:
    - `not rendered in guest mode`
  - any shared shell control that explains a missing account-owned history or
    recovery capability:
    - `disabled + tooltip`

#### Regler

- guest-allowed:
  - create, edit, and clear smart rules tied to the browser-owned roster workspace
- browser-owned:
  - seating preferences and relationship rules
- account-only:
  - none on the core rule-authoring controls

#### Import preview

- guest-allowed:
  - roster import preview through the dedicated public helper route only
- browser-owned:
  - parsed preview output becomes durable only if the user explicitly saves it
    into the guest roster workspace
  - preview responses themselves are request-scoped and disposable
- account-only:
  - owner-scoped import endpoints or any saved import history:
    - `not rendered in guest mode`

#### Smart runs

- guest-allowed:
  - smart grouping or smart seating runs only through explicit stateless public
    helper/compute seams approved for guest mode
  - if a guest-capable public smart-run seam is not present for a workspace,
    that capability stays blocked rather than falling through to authenticated
    APIs
- browser-owned:
  - draft inputs, smart-rule choices, accepted smart-run results, and any
    guest-visible continuity remain in the browser-owned snapshot only
- account-only:
  - authenticated run history, job recovery, and server-owned progress
    surfaces:
    - `not rendered in guest mode`
  - a shared smart-run control may stay visible only when it explains the
    missing capability better than removing it:
    - `disabled + tooltip`

#### Local draft continuity and export-backed checkpoints

- guest-allowed:
  - resume the current local grouping or seating draft in the same browser
  - keep guest-local checkpoint descriptors created from successful guest
    direct-download exports
  - use smart `use_history` only against guest-local export-backed checkpoints
- browser-owned:
  - active draft continuity, dismissed-state UI, and export-backed checkpoint
    descriptors remain in the guest snapshot and are later importable on
    authenticated upgrade
- account-only:
  - authenticated draft history drawers, cross-device recovery, Vault/MyFiles
    artifact history, and resumable export-job history:
    - `not rendered in guest mode`

#### Export surfaces

- guest-allowed:
  - same visible export entry point where possible
  - immediate direct-download export only
- browser-owned:
  - any guest-visible checkpoint payload captured for later upgrade comes from
    the browser-owned workspace/export event, not from an account-owned job
    record
- account-only:
  - Vault/MyFiles targets:
    - `not rendered in guest mode`
  - resumable job recovery:
    - `not rendered in guest mode`

#### Recovery, history, and job affordances

- guest-allowed:
  - none beyond the local continuity and export-backed checkpoint behavior
    frozen above
- account-only:
  - authenticated recovery/job surfaces:
    - `not rendered in guest mode`
  - one shared shell control that explains an unavailable account-only feature
    without harming the guest workflow:
    - `disabled + tooltip`

## Implementation plan

1. Freeze the three open decisions above inside this PR.
2. Extend the capability matrix by surface with the exact guest/account
   behavior for each affected affordance, including import preview, smart runs,
   and guest-local export-backed checkpoint continuity.
3. Mirror that frozen contract in the public Klassrumskartan host and guest
   workspace implementation.
4. Keep export direct-download only and block account-owned recovery/history
   surfaces according to the frozen matrix.
5. Prove unchanged authenticated behavior plus guest/reset/export/first-auth
   upgrade flows with focused browser verification.

## Detailed implementation decisions

The remaining implementation for this PR is now intentionally treated as one
broader guest-controller buildout. The older checkpoints 2-4 remain useful as
review vocabulary, but they are no longer hard delivery boundaries for the code
shape.

### 1. Public/authenticated boundary stays hard

Locked decision:
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.vue`
  remains the authority split
- authenticated host continues to render the authenticated route shell only
- public host continues to render a guest-owned controller/view only
- `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerRouteShell.ts`
  must not become a hidden dual-mode controller

### 2. Immediate rename from guest overview shell to guest controller

Locked decision:
- `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestOverviewShell.ts`
  will be renamed immediately rather than kept as a temporary wrapper
- the replacement name should describe the broader responsibility:
  `useClassroomPlannerGuestController.ts`
- the renamed controller owns the public guest workspace beyond overview-only
  state

### 3. One broader guest controller, not separate per-checkpoint controllers

Locked decision:
- the public guest lane should converge on one controller that owns:
  - bootstrap from guest snapshot storage
  - roster/template CRUD and selection
  - guest grouping/seating draft continuity
  - smart-rule persistence
  - guest export/direct-download state
  - account-only affordance policy for the public shell
- do not create a second temporary guest-only controller just to avoid touching
  later guest capabilities

### 4. Snapshot mutations stay explicit and testable

Locked decision:
- browser-owned persistence must be expressed through focused guest snapshot
  mutation helpers, not ad hoc inline object surgery spread across views
- the guest controller orchestrates those helpers and storage writes
- authenticated owner-scoped orchestration stays separate and unchanged

### 5. Reuse presentation, inject transport

Locked decision:
- shared presentation components and modals should be reused wherever they are
  transport-agnostic
- guest mode injects browser-owned save/delete handlers plus explicit public
  helper paths rather than reusing authenticated API defaults
- if a public/stateless helper seam is absent, that guest capability stays
  blocked instead of falling through to `/api/v1/apps/...`

### 6. Public import preview seam

Locked decision:
- roster import preview in guest mode must use:
  `/api/v1/public/apps/classroom.group-seating-studio/rosters/import-preview`
- the existing modal/import composable contract should stay transport-focused
  and receive that path by injection
- guest mode must not use the authenticated import-preview path as fallback

### 7. Checkpoint-3 stops before smart rules and export

Locked decision:
- checkpoint 3 is only guest grouping/seating draft continuity
- smart-rule authoring/persistence, export, and export-backed checkpoint UX are
  the following slice unless checkpoint-3 implementation proves one tiny seam is
  strictly required to keep the snapshot model coherent
- do not absorb guest smart-run/public-compute design into checkpoint 3 while
  no approved public smart-run seam exists in code

### 8. Existing PR-0223 Playwright proof is extended in place

Locked decision:
- update
  `scripts/playwright_pr_0223_public_guest_overview_checkpoint2_check.py`
  instead of creating a second overlapping PR-0223 public-route script
- the script keeps the existing overview/browser-owned/network-audit proof and
  adds checkpoint-3 guest grouping/seating continuity coverage
- if the checkpoint-2-only filename becomes too misleading later, rename once
  at final PR-0223 close-out rather than spawning parallel proof scripts now

## Execution checklist

- [x] Checkpoint 1 delivered: public route renders the real overview shell from
  browser-owned guest snapshot state without owner-scoped planner/catalog/
  draft/export API calls
- [x] Rename
  `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestOverviewShell.ts`
  to
  `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts`
  and update the public host/import sites immediately
- [x] Extend the guest controller to own browser-owned roster/template CRUD,
  selection, and modal orchestration
- [x] Inject guest roster import preview through the dedicated public helper
  route only
- [x] Persist guest roster/template mutations into the guest snapshot lane
- [x] Extend the guest controller to own guest grouping/seating draft/session
  continuity without reusing authenticated draft/workspace endpoints
- [x] Implement checkpoint-3 guest draft/session helpers in new focused modules
  instead of growing `classroomPlannerGuestControllerSupport.ts` or
  `classroomPlannerGuestOverviewCrud.ts` into mixed-responsibility files
- [x] Re-enable only the guest-capable `Grupper` / `Sittplatser` paths in the
  public shell while leaving `Regler`, export polish, and account-only
  recovery/history/job surfaces blocked or omitted
- [ ] Extend the guest controller to own guest smart-rule persistence in the
  browser-owned snapshot
- [ ] Keep guest export direct-download only and omit/block account-owned
  recovery, job, and Vault/MyFiles affordances according to the frozen matrix
- [x] Preserve the same public shell and final-state guest system message from
  checkpoint 1
- [x] Keep authenticated Klassrumskartan behavior unchanged
- [x] Add or update focused tests for the broader guest-controller lane,
  including overview authoring and public-helper injection
- [x] Add focused checkpoint-3 tests for guest draft/session continuity:
  - `src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts`
    keeps controller-level guest bootstrap, browser snapshot hydration, and
    draft/session continuity coverage
  - `src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`
    proves the dedicated guest planner shell preserves overview-selected
    classroom state, keeps `Sittplatser` enabled honestly, and round-trips
    `Sittplatser -> Grupper` without selector drift
  - `src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts`
    proves the public overview shell swaps cleanly into the dedicated guest
    planner shell while unfinished guest surfaces stay blocked honestly
- [x] Extend
  `scripts/playwright_pr_0223_public_guest_overview_checkpoint2_check.py`
  in place so the targeted browser proof now covers:
  - overview authoring
  - guest grouping draft creation/resume
  - guest seating draft creation/resume
  - reload continuity in the same browser workspace
  - unchanged owner-scoped API blocking/network audit
- [x] Run the required verification stack:
  - `pdm run fe-test src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts`
  - `pdm run fe-type-check`
  - `python -m py_compile scripts/playwright_pr_0223_public_guest_overview_checkpoint2_check.py`
  - `pdm run python -m scripts.playwright_pr_0223_public_guest_overview_checkpoint2_check --base-url http://127.0.0.1:5173`
  - `pdm run docs-validate`
- [x] Gather live public-route proof on
  `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` showing:
  - guest can create, edit, and delete a roster in the browser-owned workspace
  - guest can create, edit, and delete a room template in the browser-owned
    workspace
  - the final registration/system message still looks correct
  - no owner-scoped authenticated planner/catalog/draft/export API seam is used
- no pseudo-working dead ends

Review questions:
- do guest smart rules behave as first-class local authoring state?
- if a guest smart-run seam exists for the workspace, does it stay stateless
  and browser-owned end-to-end?
- if a guest smart-run seam does not exist yet, is the control blocked honestly
  instead of leaking into authenticated APIs?
- does guest `use_history` read only guest-local export-backed checkpoints?
- is guest export immediate-download only?
- do focused browser/network proof and guest adapter/controller tests show that
  guest smart-run, export, and history behavior never falls through to
  owner-scoped authenticated APIs?
- are account-only affordances blocked in the minimal, clean way approved in
  this PR?

## Architectural rule for implementation

This slice should separate presentation parity from orchestration parity.

That means:
- reuse the existing Klassrumskartan views and components where they are
  presentation-focused
- create a dedicated guest workspace adapter and guest draft/session lane for
  browser-owned state
- do not turn the authenticated owner-scoped route shell into a broad
  `hostMode` switch with two persistence models hidden inside it

The intent is to achieve “the same teacher tool with different storage and
access boundaries,” not “one controller that conditionally pretends to be two
products.”

## Verification plan

- `pdm run precommit-run`
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run`
- `pdm run docs-validate`
- checkpoint-3 focused verification target:
  - `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/classroomPlannerGuestDraftSession.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/PublicAppHostView.spec.ts src/views/apps/components/CreateRosterModal.spec.ts src/views/apps/components/CreateRoomTemplateModal.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run docs-validate`
  - `pdm run python -m scripts.playwright_pr_0223_public_guest_overview_checkpoint2_check --base-url http://127.0.0.1:5173`
- required evidence for checkpoints 2 through 4:
  - focused browser/network proof that guest flows call only the dedicated
    public helper namespace or stay fully local in the browser, and never hit
    owner-scoped authenticated `/api/v1/apps/classroom.group-seating-studio/...`
    endpoints
  - focused adapter/controller tests around guest snapshot hydration and guest
    draft/session orchestration so the guest lane is proven structurally, not
    only visually
- focused browser proof for:
  - guest authoring continuity for rosters, templates, and checkpoint-3 drafts
  - guest roster import preview through the public helper route only
  - guest-local grouping/seating draft resume after returning to overview and
    after page reload in the same browser workspace
  - guest-local export-backed checkpoint continuity once export ships in the
    later slice
  - guest smart-run behavior:
    - if a guest-capable public smart-run seam ships in this slice, prove it
      stays stateless and browser-owned
    - if a guest-capable public smart-run seam does not ship for a workspace,
      prove the control is blocked honestly and never falls through to
      authenticated APIs
  - guest system message placement and registration link
  - `Kasta`
  - direct-download guest export without Vault/MyFiles or resumable recovery UI
  - blocked account-only affordances by surface
  - registration without session does not trigger guest upgrade
  - later real login, then first authenticated Klassrumskartan visit prompts
    upgrade
  - unchanged authenticated grouping export recover/download flow
  - unchanged authenticated seating export recover/download flow
  - unchanged authenticated Klassrumskartan host behavior after guest import,
    postpone, discard, or when no guest state exists
