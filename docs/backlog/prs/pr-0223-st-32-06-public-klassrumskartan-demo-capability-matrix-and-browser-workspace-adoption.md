---
type: pr
id: PR-0223
title: "ST-32-06: public Klassrumskartan demo capability matrix and browser-workspace adoption"
status: ready
owners: "agents"
created: 2026-04-05
updated: 2026-04-05
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
contract and authenticated upgrade boundary. What remains before implementation
starts is not the overall direction, but a small set of still-unfrozen
guest-mode details that need one explicit contract inside this PR so the
implementation does not drift.

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

## Suggested execution flow

The implementation should be executed as four explicit checkpoints. The goal is
to keep every checkpoint reviewable, runnable, and honest rather than creating
one large guest-mode merge that mixes product decisions, orchestration changes,
and UI parity work.

### Checkpoint 1. Guest overview adapter

Intent:
- replace the current public-host placeholder/stub with the real
  Klassrumskartan shell
- keep the UI visually aligned with the authenticated app
- avoid touching authenticated owner-scoped APIs

Why this comes first:
- it proves the correct architectural seam before draft/history/export work
- it lets the public host stop looking like a separate demo product
- it creates a stable home for the small system message and later lock states

Implementation shape:
- introduce a dedicated guest workspace adapter for the public host
- derive browser-owned:
  - available rosters
  - available templates
  - selected roster/template UI state
  - overview workspace summary
- continue to use the existing browser snapshot contract and storage seam

Primary files/seams:
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.vue`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshot.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestStorage.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshotMapping.ts`

Non-goals:
- no guest draft lifecycle yet
- no smart-rule authoring yet
- no guest export yet
- no changes to authenticated route-shell orchestration

Review questions:
- does the public route now feel like the same product as authenticated
  Klassrumskartan?
- is the guest system message subtle, singular, and correctly placed?
- is browser-owned overview state clearly separated from authenticated APIs?

### Checkpoint 2. Browser-owned roster and template authoring

Intent:
- make the overview workspace genuinely useful in guest mode
- reuse the same authoring modals and import affordances rather than inventing
  guest-only UI

Why this comes second:
- roster/template authoring is the lowest-risk browser-owned persistence lane
- it validates the injected transport seams before draft/state complexity is
  introduced

Implementation shape:
- wire the public host through the injected save/delete/import-preview seams
- keep roster import preview on the stateless public helper namespace
- persist created/edited/deleted rosters and templates directly into the
  browser-owned snapshot

Primary files/seams:
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRosterModal.vue`
- `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue`
- `frontend/apps/skriptoteket/src/views/apps/useClassListImportFlow.ts`
- public guest workspace adapter introduced in checkpoint 1

Non-goals:
- no authenticated draft endpoints
- no owner-scoped roster/template CRUD calls from the public route
- no guest-specific alternate overview layout

Review questions:
- can a guest create, edit, delete, and import a roster without hitting
  authenticated APIs?
- can a guest create, edit, and delete a room template with browser-owned
  persistence only?
- does the public route still look and behave like normal Klassrumskartan?

### Checkpoint 3. Guest draft/session adapter

Intent:
- enable `Grupper` and `Sittplatser` in guest mode without reusing the
  authenticated draft/session lifecycle
- preserve the same planner shell while swapping orchestration, not visuals

Why this is a separate checkpoint:
- this is the first genuinely complex state transition lane
- draft/session logic is where accidental coupling to owner-scoped APIs is most
  likely
- keeping it separate makes architectural review much easier

Implementation shape:
- add a guest draft/session controller for:
  - create or resume grouping draft
  - create or resume seating draft
  - local switching between overview and planner workspaces
- hydrate planner-friendly shapes from the guest snapshot instead of from the
  authenticated draft/workspace endpoints
- reuse the existing planner panes and shell where they are presentation-only

Primary files/seams:
- guest workspace adapter introduced in checkpoint 1
- guest mapping/hydration seam in
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshotMapping.ts`
- planner shell components under
  `frontend/apps/skriptoteket/src/views/apps/components/`

Non-goals:
- no hidden conditional branch that turns the authenticated route shell into a
  two-personality controller
- no account-owned draft persistence
- no export recovery surfaces

Review questions:
- does the public planner now use browser-owned drafts end-to-end?
- are `Grupper` and `Sittplatser` using the same shell language as
  authenticated mode?
- has authenticated route-shell behavior remained unchanged?

### Checkpoint 4. Smart rules, export, and account-only affordances

Intent:
- finish the guest capability matrix honestly
- enforce the final boundary between browser-owned guest work and
  account-owned/app-owned features

Why this is last:
- it depends on the guest overview and guest draft lanes already being real
- it is where the final product honesty is expressed in the UI

Implementation shape:
- persist guest smart rules in the browser-owned snapshot
- keep smart compute stateless and server-assisted only when needed through
  explicit guest-capable public helper seams
- if a guest-capable smart-run seam is not yet present for one workspace, keep
  that affordance honestly blocked rather than routing guest mode through the
  authenticated owner-scoped APIs
- provide direct-download export only from the normal export entry point
- omit account-owned recovery/job/Vault surfaces from guest mode
- use disabled + tooltip only where showing the control improves comprehension

Primary files/seams:
- guest workspace adapter
- guest draft/session controller
- smart-rule surfaces in `Regler`
- grouping/seating export entry points

Non-goals:
- no guest Vault/MyFiles
- no resumable export jobs in guest mode
- no pseudo-working dead ends

Review questions:
- do guest smart rules behave as first-class local authoring state?
- if a guest smart-run seam exists for the workspace, does it stay stateless
  and browser-owned end-to-end?
- if a guest smart-run seam does not exist yet, is the control blocked honestly
  instead of leaking into authenticated APIs?
- does guest `use_history` read only guest-local export-backed checkpoints?
- is guest export immediate-download only?
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
- focused browser proof for:
  - guest authoring continuity for rosters, templates, smart rules, and drafts
  - guest roster import preview through the public helper route only
  - guest-local draft resume and guest-local export-backed checkpoint
    continuity in the same browser workspace
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
