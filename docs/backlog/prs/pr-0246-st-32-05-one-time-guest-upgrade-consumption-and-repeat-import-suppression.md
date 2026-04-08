---
type: pr
id: PR-0246
title: "ST-32-05 follow-up: one-time guest-upgrade consumption and repeat-import suppression"
status: done
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
stories:
  - "ST-32-05"
tags:
  [
    "frontend",
    "klassrumskartan",
    "guest-upgrade",
    "import-policy",
    "one-time-bridge",
    "browser-state",
  ]
dependencies:
  - "ADR-0079"
  - "ST-32-04"
  - "ST-32-05"
  - "PR-0221"
  - "PR-0233"
  - "PR-0245"
acceptance_criteria:
  - "Given the authenticated Klassrumskartan host commits a guest-upgrade request and receives a receipt that proves meaningful processing occurred, when the commit succeeds, then the backend records one canonical consumption fact for that user and app and the browser-owned guest snapshot is cleared."
  - "Given the same browser later reaches authenticated Klassrumskartan again after a prior consuming guest-upgrade commit, when stale guest snapshot data still exists locally, then the authenticated host may use the backend-owned canonical fact to clear that stale local state silently and does not show the import prompt again."
  - "Given the same browser later reaches public Klassrumskartan after a prior authenticated Klassrumskartan entry, when the browser loads the public guest shell, then it relies on the browser-owned authoring-closure marker only, does not initialize a new upgrade-capable guest workspace, and instead blocks with a clear login-first message."
  - "Given a guest-upgrade commit returns a structurally suspicious all-zero `200` receipt, when the authenticated host resolves the result, then it does not consume the one-time bridge, does not write the backend consumption fact, and keeps the truthful error/prompt lane introduced by `PR-0245`."
  - "Given a guest-upgrade commit imports some entities but also reports conflicts, when the authenticated host resolves the result, then the teacher sees one truthful post-import outcome summary for what was created, reused, or left unchanged and is not trapped in an unresolvable repeat-import prompt."
  - "Given a browser opens authenticated Klassrumskartan before any guest-upgrade import happens, when the same browser later visits the public Klassrumskartan host, then it does not create a new upgrade-capable guest snapshot and a later authenticated visit does not reopen the guest-upgrade prompt from that path."
---

## Status note

This PR is implemented locally and verified. The shipped shape keeps the two
approved concepts separate:

- backend ledger answers only whether a meaningful authenticated guest-upgrade
  import was consumed
- browser markers answer only whether this browser may still create new
  upgrade-capable guest work

## Problem

Live testing on 2026-04-08 exposed that the current guest-upgrade lane still
behaves like a reusable loop:

- a browser can keep creating new guest snapshots even after a first account
  registration/import bridge has already been used
- a partial import with conflicts keeps the browser snapshot alive, so the same
  prompt can return on later logins even though parts of the guest work already
  moved into the authenticated account
- the product ends up designing around repeated logged-out/logged-in import
  attempts, snapshot de-dupe, and conflict recovery paths that are not aligned
  with the intended one-time onboarding bridge

The product decision is now explicit: Klassrumskartan guest-upgrade is a
one-time bridge for first-account continuity in one browser, not a permanent
offline/online synchronization mode.

## Goal

Define a robust one-time guest-upgrade consumption model for Klassrumskartan
that:

- gives the backend a canonical yes/no fact for whether a user has already
  consumed the bridge in authenticated policy
- keeps the same-browser UX decisive by consuming local guest state after a
  meaningful authenticated import commit
- prevents further repeat-import prompts or new upgrade-capable guest work in
  that same browser after the bridge has been used, without making the public
  namespace depend on user-specific backend truth

## Non-goals

- No new multi-import conflict-resolution center.
- No attempt to preserve browser-owned upgrade snapshots indefinitely after the
  first authenticated import attempt.
- No redesign of the broader authenticated planner information architecture.
- No change to the existing authenticated guest-upgrade API route shape.

## Options considered

### Option A: browser-only one-time marker

Store a permanent `bridge-consumed` marker only in browser storage and let the
frontend/public shell suppress future prompts from that local fact alone.

Pros:

- smallest frontend-only surface
- directly aligned with the same-browser product rule
- no migration or backend schema work

Cons:

- no backend ground truth for support, auditing, or deterministic policy checks
- easy to lose or reset through browser storage clearing
- cannot answer the product question "has this user already consumed the
  bridge?" without inference
- leaves authenticated flows depending on local state that may be stale or
  absent

Assessment:

- good as a UX hint
- not sufficient as the canonical solution

### Option B: infer consumption from existing imported planner artifacts

Keep the current model and infer "already imported" from existing
`guest_import_identity`, checkpoints, imported drafts, or related planner rows.

Pros:

- avoids new persistence primitives
- reuses data already written by the import lane

Cons:

- not a canonical fact; it is still inference
- partial imports make the answer ambiguous
- a user may import some entities but not others, which makes artifact-based
  inference brittle and hard to explain
- couples a product-policy question to implementation details of drafts and
  checkpoint dedupe

Assessment:

- better than browser-only guesswork
- still too indirect for a dependable product rule

### Option C: backend-only canonical consumption fact

Add a durable backend record that a given user has consumed the Klassrumskartan
guest-upgrade bridge, and rely on that alone for future suppression logic.

Pros:

- gives the backend one authoritative yes/no answer
- easy to inspect, audit, and reason about in support/debugging
- decouples the policy from planner draft/checkpoint internals

Cons:

- public signed-out browser behavior still needs some local handling to avoid
  recreating upgrade-capable guest state before login
- same-browser stale snapshot cleanup becomes clumsier if the frontend has to
  rediscover everything from the server
- does not by itself solve leftover browser state

Assessment:

- strong on truth and policy
- incomplete on same-browser UX by itself

### Option D: hybrid model with backend canonical fact plus browser consumed marker

Persist one backend-owned canonical consumption record per user/app, and also
persist a browser marker used to suppress stale local guest state and block
same-browser re-entry into the upgrade-capable public workspace.

Pros:

- backend has authoritative ground truth
- frontend/public flows still get a fast, clear same-browser control point
- browser cleanup and backend policy reinforce each other instead of competing
- support/debugging can inspect one durable fact while the product keeps the
  strict one-time bridge UX

Cons:

- touches both backend and frontend state seams
- requires clear precedence rules between server truth and local browser state
- adds one new persistence concept that must be documented carefully

Assessment:

- highest clarity and strongest operational story
- best fit for the product direction and debugging needs surfaced in live
  testing

## Implemented direction

Proceed with **Option D**:

- backend-owned canonical one-time consumption fact per user/app for
  authenticated policy only
- browser-owned authoring-closure marker for same-browser public suppression
- meaningful authenticated guest-upgrade receipts consume the bridge even when
  they include mixed conflict outcomes
- structurally suspicious all-zero `200` receipts do not consume the bridge and
  stay on the `PR-0245` truthful error lane

Why this is the recommended shape:

- it gives a dependable backend answer to the user-level question
  "has this bridge already been used?"
- it keeps public and authenticated hosts within the already-approved
  `ADR-0079` authority boundary
- it keeps same-browser behavior decisive without adding user-specific logic to
  the public bootstrap/helper namespace
- it avoids designing a long-tail resync/conflict-resolution system around a
  workflow the product does not want to support

## Implementation notes

- Backend:
  - added a dedicated guest-upgrade consumption ledger plus migration
  - added an authenticated consumption-status read seam
  - made ledger writes race-safe with PostgreSQL `ON CONFLICT DO NOTHING`
- Frontend:
  - added a browser-owned `guest-authoring-closed` marker
  - first authenticated Klassrumskartan entry closes new guest authoring in that
    browser
  - public host stays browser-marker-only and cookie-agnostic
  - later public visits in the same browser block instead of auto-creating a
    new guest snapshot
  - later authenticated visits use backend truth plus local cleanup and do not
    reopen the prompt from the approved `E2` path

## Verification

- `pdm run docs-validate`
- `pdm run fe-type-check`
- `pdm run pytest tests/integration/infrastructure/repositories/test_classroom_planner_guest_upgrade_repository.py`
- `pdm run pytest -m docker --override-ini addopts='' tests/integration/test_migration_0f4c2d7a9b1e_idempotent.py -q`
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts`
- live browser proof on 2026-04-08 against `http://127.0.0.1:5173`:
  - authenticated Klassrumskartan entry set `skriptoteket:classroom-planner:guest-authoring-closed = true`
  - no guest snapshot pointer or IndexedDB guest snapshot record existed
  - later public visit in the same browser showed the blocked login-first state
    and still created no guest snapshot
  - later authenticated revisit showed no guest-upgrade prompt reopening from
    that path

## Decision gates for review

- Should the canonical backend fact be stored as a tiny dedicated
  user/app-consumption ledger rather than inferred from planner entities?
  Recommendation: yes.
- Should the bridge be consumed on every successful commit response?
  Recommendation: no.
- Should mixed receipts that show meaningful processing plus conflicts still
  consume the one-time bridge?
  Recommendation: yes.
- Should the browser keep any retry-capable upgrade snapshot after that first
  consuming outcome?
  Recommendation: no.

## Edge-case scenario: account-first, guest-later

Scenario:

- the teacher creates an account
- logs in and uses authenticated Klassrumskartan first
- later logs out
- later enters the public Klassrumskartan route in the same browser and creates
  meaningful guest work
- later logs back in and returns to authenticated Klassrumskartan

Current behavior before `PR-0246`:

- the public guest shell auto-initializes a browser snapshot when no current
  snapshot exists
- later authenticated Klassrumskartan checks only for that browser snapshot
- so this scenario currently produces a later import prompt even though the
  teacher had already used the authenticated planner before creating that guest
  work

### Decision table

| Browser history in this browser | Later public visit behavior | Later authenticated visit behavior | Import prompt allowed? | Recommended? |
|---|---|---|---|---|
| No prior authenticated Klassrumskartan visit; no prior consuming import | Public guest workspace may initialize normally | Authenticated host may offer the first guest-upgrade prompt if meaningful guest state exists | Yes | Yes |
| Prior authenticated Klassrumskartan visit; no prior guest-upgrade consumption fact | Public guest workspace should not initialize a new upgrade-capable snapshot; show login-first guidance instead | Authenticated host opens the normal planner without guest-upgrade prompt unless stale pre-closure guest state exists locally | No | Yes |
| Prior consuming guest-upgrade commit in this browser and backend ledger says consumed | Public guest workspace should not initialize; rely on browser marker only and show login-first guidance | Authenticated host may use backend truth to repair stale local state and must not show a repeat-import prompt | No | Yes |
| Prior authenticated visit but browser closure marker is missing and a later guest snapshot was still created | Public guest workspace may still initialize under current code; this is the gap `PR-0246` closes | Authenticated host should treat this as stale/invalid guest state once the stricter closure rule ships | No after remediation | Transitional only |
| All-zero suspicious `200` commit receipt with guest snapshot still present | Public guest workspace remains governed by browser state; no consumption/closure should be inferred from the bad receipt | Authenticated host must stay on the truthful `PR-0245` prompt/error lane and keep the snapshot non-consuming | Yes, because bridge not consumed | Yes |

Options:

### Option E1: allow one import until the first meaningful guest-upgrade commit

Pros:

- smallest change relative to the current hybrid model
- keeps the bridge available until it is truly consumed by import

Cons:

- still allows the exact post-account guest-work loop the product wants to
  avoid
- keeps a confusing path where an already-established account owner can drift
  back into browser-owned guest state

### Option E2: close guest-upgrade eligibility in the browser on first authenticated Klassrumskartan entry

Pros:

- best matches the product intention that guest-upgrade is an onboarding bridge
  rather than an ongoing alternate workspace mode
- prevents accidental post-account guest work before it starts
- keeps the rule simple for teachers: once this browser has entered the real
  planner, use login rather than public guest mode

Cons:

- stricter than a pure "first import consumes" rule
- same browser on a shared machine would no longer offer public guest authoring
  after authenticated use unless storage is intentionally cleared
- introduces a second browser-owned state concept unless carefully named and
  documented

Recommendation:

- prefer **Option E2**
- treat first authenticated Klassrumskartan entry in a browser as the point
  where new upgrade-capable guest authoring should close in that browser, even
  if no import happened on that first authenticated visit
- keep this closure browser-owned, not public-backend-driven, so `ADR-0079`
  remains intact
- keep the backend canonical fact focused on actual guest-upgrade consumption,
  not generic app visitation

### Reviewable policy statement

For re-review, the proposed policy should now be read as:

1. The one-time **import bridge** is consumed only by a meaningful authenticated
   guest-upgrade commit.
2. The browser's **guest-authoring eligibility** closes earlier, on first
   authenticated Klassrumskartan entry in that browser, to prevent the
   account-first/guest-later loop.
3. Those are separate concepts on purpose:
   - backend ledger answers whether an import bridge was actually consumed
   - browser marker answers whether this browser may still create new
     upgrade-capable guest work

## Proposed implementation shape

1. Add a dedicated backend seam for one canonical Klassrumskartan
   guest-upgrade-consumption fact per user/app, read only from authenticated
   seams.
2. Extend the browser guest-storage seam with:
   - a one-time upgrade-consumed marker for Klassrumskartan
   - a separate browser-owned closure marker if review approves the stricter
     account-first `E2` policy above
3. Update authenticated guest-upgrade orchestration so meaningful commit
   responses:
   - records the backend consumption fact
   - consumes the browser snapshot
   - records the one-time marker
   - shows a truthful outcome summary instead of returning to the prompt
4. Keep suspicious all-zero `200` receipts non-consuming:
   - no backend write
   - no browser consumption marker
   - no final success summary
   - remain on the `PR-0245` truthful prompt/error lane
5. Update the public guest shell so it consults browser-owned markers only and
   never the backend consumption fact:
   - does not reinitialize an upgrade-capable guest snapshot
    - presents a clear login-first affordance instead
6. Replace the existing card-based import result surface with compact
   text-first outcome copy that can explain partial imports without implying
   the teacher can keep retrying the same guest snapshot forever.

## Test plan

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_guest_upgrade_partial_conflict_ground_truth.py -q`
- `pdm run fe-test -- --run src/views/apps/classroomPlannerGuestStorage.spec.ts src/views/apps/useClassroomPlannerGuestUpgradeOneTime.spec.ts src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts`
- Explicit proof for the approved account-first/guest-later `E2` path:
  - seed a browser with prior authenticated Klassrumskartan entry but no prior
    import consumption
  - verify the public route does not create a new upgrade-capable guest
    snapshot and instead shows login-first guidance
  - verify the later authenticated route does not reopen a guest-upgrade prompt
    from that post-account public visit path
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live browser proof on:
  - `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
  showing first import consumption plus later signed-out public re-entry
  blocking in the same browser context

## Rollback plan

- Revert the one-time browser marker, authenticated guest-upgrade consumption,
  and public guest blocking surface together if the first-import bridge stops
  working.
- Keep rollback narrow; do not revert the earlier backend guest-upgrade route
  hardening already shipped in `PR-0221`, `PR-0233`, and `PR-0245`.

## References

- Story owner:
  [ST-32-05](../stories/story-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy.md)
- Accepted public guest-state boundary ADR:
  [ADR-0079](../../adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md)
- Initial authenticated guest-upgrade foundation:
  [PR-0221](pr-0221-st-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy-foundation.md)
- Template-reuse/remap hardening:
  [PR-0233](pr-0233-st-32-05-follow-up-authenticated-guest-upgrade-template-reuse-and-seat-remap-hardening.md)
- Empty-snapshot/no-op reconciliation:
  [PR-0245](pr-0245-st-32-05-empty-guest-snapshot-and-zero-effect-import-ui-reconciliation.md)
