---
type: pr
id: PR-0232
title: "ST-32-06: guest local draft parity, direct-download export, and account-only history affordance polish"
status: ready
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-32-06"
tags:
  [
    "frontend",
    "backend",
    "klassrumskartan",
    "public-access",
    "guest-workspace",
    "export",
    "history",
  ]
dependencies:
  - "ADR-0079"
  - "ADR-0080"
  - "ST-32-05"
  - "EPIC-29"
  - "PR-0229"
  - "PR-0223"
  - "PR-0233"
  - "PR-0234"
acceptance_criteria:
  - "Given shared planner toolbar overflow no longer keeps undo/redo visibly pinned after `PR-0229`, when guest users trigger undo or redo from the toolbar or keyboard shortcuts, then grouping and seating undo/redo work as browser-owned local editing state with the same shortcut parity as the authenticated workspace."
  - "Given guest exports grouping or seating work, when the shared export entry point is used, then export delivers an immediate direct download only through dedicated public routes under `/api/v1/public/apps/classroom.group-seating-studio/grouping/export` and `/api/v1/public/apps/classroom.group-seating-studio/seating/export`, and does not render Vault/MyFiles targets, resumable export-job recovery, or other authenticated artifact-history surfaces."
  - "Given guest export starts from browser-owned draft state, when export is triggered immediately after a guest edit, then the guest export boundary first flushes the same pending draft/smart-rule state that the shared planner export seam requires before serializing the export request, so the downloaded artifact and later authenticated upgrade prompt both reflect the latest guest-visible workspace."
  - "Given guest export may still capture browser-owned checkpoint payloads or descriptors for later authenticated upgrade, when those payloads are stored locally, then they are not treated as guest Smart-history inputs and are not wired to `Use history`."
  - "Given guest export writes browser-owned checkpoint descriptors for later authenticated upgrade, when a newly exported grouping or seating arrangement matches an existing guest checkpoint fingerprint, then the guest snapshot dedupes that checkpoint instead of appending duplicates."
  - "Given guest mode still needs honest account-only boundaries, when history, recovery, or job affordances render, then authenticated history drawers, job recovery surfaces, and other account-owned continuity affordances stay omitted or minimally blocked according to the explicit guest/auth affordance table in this PR without any fallback into `/api/v1/apps/classroom.group-seating-studio/...` export, history, recovery, or download routes."
  - "Given authenticated Klassrumskartan already has export-job recovery and server-owned history semantics, when this guest slice ships, then the authenticated export/history flows remain unchanged."
  - "Given new public export helper routes are added for guest continuity, when they are reviewed, then they publish rate limits, payload caps, time budgets, validation rules, and cookie-agnostic semantics consistent with `ADR-0079`."
  - "Given registration in the current auth model does not establish an authenticated Klassrumskartan import session, when a guest user registers after local guest export work, then no import runs during registration; and when the same user later reaches the authenticated Klassrumskartan host with a real session, then the pending guest snapshot offered for `import` / `discard` / `postpone` still carries the deduped export-backed checkpoint continuity created in this slice."
---

## Problem

After `PR-0223`, the guest browser workspace can author rosters, templates, and
planner drafts, but it still falls short in three places that now matter more
because the guest surface is intentionally reusing the authenticated planner
chrome:

- guest undo/redo is still a no-op even though undo/redo is local editing state
- guest export is still hidden instead of using the same visible export entry
  point with a different transport boundary
- the remaining account-only history and recovery affordances are not yet
  fully frozen in the public shell

Those are one coherent slice because they all define the difference between
guest local continuity and authenticated durable continuity.

## Goal

Finish the honest guest-local continuity layer:

- make guest undo/redo real and keyboard-parity-safe
- add guest direct-download export through the shared entry points
- keep any guest-local checkpoint capture limited to browser-owned continuity or
  later authenticated upgrade
- finish the account-only affordance policy for history, recovery, jobs, and
  artifact surfaces

## Non-goals

- Guest `Regler` enablement or solver-based Smart-run parity
- Reintroducing guest `Use history` or history-based Smart behavior
- Changing authenticated export-job recovery, Vault integration, or
  cross-device continuity
- Silent guest fallthrough into owner-scoped authenticated export/history APIs

## Implementation plan

1. Implement guest local undo/redo.
   - Replace the guest no-op history actions with real browser-owned local
     undo/redo for grouping and seating drafts.
   - Introduce the shared planner undo/redo keyboard shortcut composable in
     this slice so guest parity does not wait on `PR-0229`.
   - Keep `PR-0229` responsible for any later toolbar-overflow polish,
     breakpoint alignment, or discoverability refinement after this slice
     lands.
   - Keep these semantics local editing state only, not authenticated history.
   - Scope the guest history stack to the browser-owned guest draft session:
     - per active draft id
     - available from both toolbar controls and keyboard shortcuts
     - preserved while the guest keeps working in the same browser session
     - not upgraded into authenticated draft-history semantics
     - not persisted as a durable undo/redo stack across guest reloads
   - Wire the shortcut handler at the shared planner-shell seam, but dispatch
     to guest-local session actions only when the public guest shell is active.
   - Keep editable text fields and menu interactions from accidentally
     swallowing or misfiring planner shortcuts.

2. Keep history boundaries honest.
   - Do not add guest history drawers or authenticated recovery surfaces.
   - Keep history-based Smart controls out of guest mode per `ADR-0080`.
   - Make sure guest local undo/redo does not imply guest durable history.
   - Keep the current guest shell omissions explicit:
     - no `Historik` drawer entry
     - no guest `Use history`
     - no resumable recovery CTA
     - no guest job/status copy that implies later retrieval from account-owned
       surfaces

3. Add guest direct-download export.
   - Reuse the same visible export entry point where possible.
   - Send guest export through explicit public direct-download routes at:
     - `/api/v1/public/apps/classroom.group-seating-studio/grouping/export`
     - `/api/v1/public/apps/classroom.group-seating-studio/seating/export`
   - Keep those routes outside the authenticated `/api/v1/apps/...` namespace.
   - Do not create resumable job rows, Vault artifacts, or recoverable guest
     export jobs.
   - Do not reuse authenticated export/history/recovery/download routes as
     guest fallbacks.
   - Keep the shared toolbar/export presentation, but swap the transport:
     - guest mode re-enables the visible export split-button in the shared
       grouping and seating toolbars
     - authenticated mode keeps the existing export-job/Vault flow unchanged
     - guest mode uses a dedicated public direct-download client helper and
       does not touch the authenticated job polling/recovery API family
   - Keep the guest request contract stateless and self-contained:
     - serialize only after the guest export-preparation boundary succeeds
     - flush pending guest draft lane changes before export
     - flush pending guest smart-rule lane changes before export when relevant
     - snapshot payload
     - expected draft revision
     - explicit export option/layout selection
   - Keep the guest response contract direct-download only:
     - attachment bytes plus HTTP download headers
     - no job id
     - no polling status
     - no recoverable export state
     - no `download_url`

4. Keep checkpoint capture scoped correctly.
   - If guest export captures checkpoint payloads or descriptors, store them
     only in the browser-owned guest snapshot.
   - Keep that payload lane importable later through the authenticated upgrade
     path.
   - Do not wire those payloads into guest `Use history`, because guest
     `Use history` does not exist.
   - Capture those checkpoint descriptors only after successful guest export.
   - Write canonical checkpoint payloads, not metadata-only placeholders, so the
     later authenticated upgrade path can continue to submit full guest
     checkpoint descriptors for server-side recomputed fingerprint dedupe.
   - Deduplicate guest checkpoint writes on the browser-owned snapshot side
     using the checkpoint fingerprint before saving:
     - identical repeated guest exports must not append duplicate checkpoints
     - dedupe must stay label-insensitive and export-artifact-insensitive in the
       same spirit as `ADR-0074`
   - Prefer local checkpoint persistence in the browser-owned guest snapshot
     rather than broadening the public export response into a guest-history API.
   - Keep checkpoint capture limited to later authenticated import continuity
     and local bookkeeping; it must not become a visible guest recovery surface.
   - Keep this aligned with the existing authenticated upgrade contract from
     `PR-0221`:
     - registration alone must not trigger import
     - the first later authenticated Klassrumskartan visit still offers the
       same `import` / `discard` / `postpone` prompt
     - server-side import remains the authoritative second dedupe boundary via
       server-recomputed snapshot and entity fingerprints

5. Finish the account-only affordance audit.
   - Remove or block authenticated history/recovery/job/Vault affordances in the
     guest toolbar, drawers, and related presentation seams according to the
     explicit table below.
   - Keep authenticated flows unchanged.
   - The guest shell should therefore end this slice with:
     - visible export affordance parity
     - real local undo/redo parity
     - continued omission of history drawers and recovery/job affordances
     - continued omission of Vault / My Files targeting language

### Guest/auth affordance table

| Surface | Guest in `PR-0232` | Authenticated remains |
|---------|--------------------|-----------------------|
| Undo / redo buttons | Visible and functional as browser-owned local draft state | Visible and backed by server-owned draft history |
| Undo / redo keyboard shortcuts | Functional through the shared shortcut contract | Functional through the shared shortcut contract |
| Export split-button | Visible and functional | Visible and functional |
| Export transport | Dedicated public direct-download route only | Existing authenticated export-job flow |
| Export status / recovery | No job id, polling, recovery CTA, or later retrieval copy | Existing job status, recovery, and download behavior unchanged |
| `Historik` toolbar/drawer affordance | Hidden / omitted | Existing history drawer behavior unchanged |
| `Use history` in Smart settings | Hidden / omitted | Existing authenticated-only behavior unchanged |
| Vault / My Files language | Hidden / omitted | Existing authenticated copy unchanged |
| Authenticated export/history/download API family | Forbidden as guest fallback | Canonical authenticated seam |
| Guest-upgrade prompt relation | Guest export/checkpoint continuity may later feed first authenticated Klassrumskartan import prompt; no registration-time import | Existing `import` / `discard` / `postpone` prompt from `PR-0221` remains canonical |

6. Publish the public export abuse-control contract.
   - Freeze the guest export routes as cookie-agnostic and non-ambient per
     `ADR-0079`.
   - Publish route-level:
     - rate limits
     - payload caps
     - request time budgets
     - validation rules
   - Reuse the public helper review pattern already established for roster
     import preview and guest Smart routes:
     - explicit public namespace
     - no `require_user_api`
     - no `require_csrf_token`
     - same semantics whether or not the browser carries an authenticated
       session cookie

## Agreed implementation shape

The final intended implementation for this PR is the boundary-first option:
shared presentation, separate guest transport/state.

### Frontend

- Replace the guest history no-ops in
  `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftSession.ts`
  with a real guest-local undo/redo controller.
- Model guest undo/redo as browser-owned draft-session history, not backend
  history:
  - snapshot workspace state after meaningful guest mutations
  - maintain undo/redo stacks per active guest draft id
  - clear or rebind stacks when the active draft changes
  - do not persist the stacks as durable history rows
- Introduce a shared planner undo/redo keyboard shortcut composable now, then
  let `PR-0229` pick up any follow-up breakpoint/overflow polish later.
- Re-enable the export split-button in the guest grouping and seating toolbars,
  but keep history/recovery affordances hidden.
- Add guest export client helpers and a guest direct-download flow instead of
  reusing the authenticated export-job polling/recovery path.
- Make guest export reuse the same pre-export discipline as the authenticated
  planner seam:
  - call the guest `prepareForExport` boundary first
  - flush pending draft work before serializing the export request
  - flush pending smart-rule work before serializing the export request when
    the active guest roster has dirty rule state
  - prove this with a test that exports immediately after a local edit
- After successful guest export, persist checkpoint descriptors into the
  browser-owned guest snapshot with fingerprint dedupe, not naive append-only
  writes.

### Backend

- Add dedicated public export routes under the public namespace only:
  - `POST /api/v1/public/apps/classroom.group-seating-studio/grouping/export`
  - `POST /api/v1/public/apps/classroom.group-seating-studio/seating/export`
- Keep those routes cookie-agnostic and non-ambient per `ADR-0079`.
- Hydrate a transient guest workspace from the submitted snapshot payload, then
  reuse the canonical export preparation/rendering seams where possible without
  creating owner-scoped draft rows, export-job rows, or Vault artifacts.
- Return direct-download bytes with attachment headers only.
- Keep the backend route contract aligned with the later import path:
  - accept canonical guest checkpoint-capable snapshot payloads
  - avoid inventing a parallel guest-only checkpoint representation
  - preserve the same browser-owned export continuity that the authenticated
    upgrade prompt may later import after a real sign-in session

### Boundary guardrails

- Guest export must never call or fall through to:
  - `/api/v1/apps/classroom.group-seating-studio/drafts/.../exports/jobs`
  - `/api/v1/apps/classroom.group-seating-studio/.../exports/jobs/recover`
  - `/api/v1/apps/classroom.group-seating-studio/.../exports/jobs/{job_id}`
  - `/api/v1/apps/classroom.group-seating-studio/.../exports/jobs/{job_id}/download`
- Guest undo/redo must never imply:
  - guest history drawers
  - guest `Use history`
  - guest durable recovery after reload
  - authenticated draft-history parity
- Guest checkpoint descriptors may continue to support later authenticated
  upgrade/import, but they must remain invisible to guest Smart/history logic.
- Guest export continuity must not weaken the `PR-0221` import boundary:
  - registration alone still does nothing
  - only a later real authenticated Klassrumskartan visit may offer import
  - imported checkpoints still dedupe from server-recomputed fingerprints

## Verified dependency

[PR-0233](pr-0233-st-32-05-follow-up-authenticated-guest-upgrade-template-reuse-and-seat-remap-hardening.md)
is now implemented and live-proven on 2026-04-07 with the real local `SA24D`
roster and `G20` classroom fixtures. Authenticated preview on the canonical
`/api/v1/apps/classroom.group-seating-studio/guest-upgrade` seam returned
`200 OK`, and the logged-in browser prompt on
`http://127.0.0.1:5173/apps/classroom.group-seating-studio` rendered without
the previous `Internal server error`.

This PR should therefore keep targeting the existing authenticated import seam
for later guest export/checkpoint continuity and must not invent a parallel
guest-only compatibility shape or fallback transport.

## Test plan

- `pdm run fe-test` targeted at:
  - guest draft-session/state specs covering undo/redo behavior
  - guest shell specs covering visible omission/blocking of account-only
    history and recovery affordances
  - shared export action specs touched by guest direct-download behavior
  - guest export flow coverage proving export flushes pending edits before
    request serialization
  - guest snapshot/checkpoint coverage proving repeated identical guest exports
    do not append duplicate checkpoint descriptors
- backend and web unit tests for:
  - the new public grouping export route
  - the new public seating export route
  - authenticated-route guardrails proving no fallback into `/api/v1/apps/...`
  - cookie-agnostic public semantics
  - validation failures
  - rate limits, payload caps, and request time budgets
  - public export behavior immediately after local guest edits
  - guest checkpoint write dedupe semantics at the browser-owned snapshot seam
- `pdm run fe-type-check`
- `pdm run docs-validate`
- focused public-route browser proof showing:
  - guest undo/redo works from both toolbar controls and keyboard shortcuts
  - guest export starts immediate download
  - guest export immediately after a local edit still includes the latest edit
  - no Vault/MyFiles or resumable recovery UI appears
  - guest export uses only the dedicated public export routes
  - guest export/history flows never call owner-scoped authenticated export or
    history endpoints
  - registration after guest work does not trigger import
  - later authenticated Klassrumskartan visit still surfaces the existing
    `import` / `discard` / `postpone` prompt with the guest snapshot continuity
    intact
  - authenticated grouping Smart/history/export flow remains unchanged
  - authenticated seating Smart/history/export flow remains unchanged

## Required quality gate

Before this PR can be closed, capture one explicit live verification pass that
proves both guest-mode behavior and authenticated non-regression on real local
planner data.

Minimum manual gate:

- Run the public guest route on
  `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` against
  the local backend and verify:
  - guest undo/redo parity from toolbar controls and keyboard shortcuts
  - guest export direct-download behavior after a local edit
  - guest transport stays on the public export seam only
- Run the authenticated route on
  `http://127.0.0.1:5173/apps/classroom.group-seating-studio` using the
  existing real local `SA24D` roster and `G20` classroom fixtures when
  available, and verify:
  - authenticated grouping history/export still behaves on the canonical
    `/api/v1/apps/classroom.group-seating-studio/...` seam
  - authenticated seating history/export still behaves on the canonical
    `/api/v1/apps/classroom.group-seating-studio/...` seam
  - no guest/public helper route is used as an authenticated fallback

Verification evidence requirement:

- Record the exact command(s), URLs, fixture names, and route families checked
  in `.agents/handoff.md`.
- The authenticated transport audit must explicitly name the canonical
  `/api/v1/apps/...` seam and state that it remained unchanged for the logged-in
  `SA24D` / `G20` pass.

## Rollback plan

- Re-hide guest export and revert guest undo/redo changes if the slice leaks
  into authenticated export/history seams or makes guest draft state unreliable.
- Leave authenticated export/history flows untouched during rollback; only the
  guest/public transport and state wiring should move.

## Review gate

- Retained review gate:
  [REV-PR-0231](../reviews/review-pr-0231-guest-smart-parity-and-local-continuity-boundary.md)
