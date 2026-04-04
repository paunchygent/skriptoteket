---
type: pr
id: PR-0221
title: "ST-32-05: authenticated guest-upgrade orchestration and idempotent import foundation"
status: done
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-32-05"
tags: ["backend", "frontend", "klassrumskartan", "guest-upgrade", "import-policy", "public-access"]
dependencies:
  - "ADR-0079"
  - "ST-32-03"
  - "ST-32-04"
  - "EPIC-27"
acceptance_criteria:
  - "Given an upgrade-capable Klassrumskartan guest snapshot exists in browser storage, when the user reaches the authenticated Klassrumskartan host after a real login session is established, then the app surfaces an explicit `import`, `discard`, or `postpone` choice instead of importing automatically."
  - "Given registration in the current auth model does not create a session cookie, when a new user registers, then no guest-upgrade orchestration runs until the first real authenticated session later exists."
  - "Given the authenticated guest-upgrade boundary is invoked, when the client submits `mode: preview` or `mode: commit`, then one authenticated orchestration endpoint processes the guest snapshot using `snapshot_id`, schema version, and full guest payload, server-side recomputes `snapshot_content_hash` and per-entity fingerprints before any dedupe/import decision, and returns structured `created`, `reused`, `skipped`, and `conflicted` receipts."
  - "Given the same authenticated user repeats the same guest-upgrade commit with an unchanged snapshot identity and content, when the backend reprocesses the request, then rosters, templates, smart-rule sets, and checkpoints dedupe from server-recomputed snapshot/entity fingerprints and imported historical drafts dedupe from one durable server-owned draft import identity / lookup seam rather than from client-submitted values alone."
  - "Given local guest rosters or templates collide with existing account-owned assets, when conflict handling runs, then exact-content matches reuse existing assets and same-name/different-content assets import non-destructively as separate assets."
  - "Given guest grouping or seating drafts collide with an existing active authenticated draft of the same roster and kind, when import policy is applied, then the guest draft imports as historical by default and replacing the current active draft remains outside this slice."
  - "Given guest checkpoints collide with existing authenticated checkpoints, when import policy is applied, then checkpoints import additively with fingerprint dedupe rather than replacing existing history."
  - "Given the guest snapshot carries `task_entry_classroom_selection_mode`, when the authenticated import pipeline processes guest drafts, then that field is preserved and consumed end-to-end rather than silently dropped."
  - "Given a pending authenticated guest-upgrade exists, when the authenticated Klassrumskartan host loads, then the upgrade prompt gates authenticated planner bootstrap until the user chooses `import`, `discard`, or `postpone` or the import attempt resolves."
  - "Given the user chooses `postpone` or the authenticated import preview/commit fails, when frontend state updates run, then local guest snapshot storage remains intact; and given authenticated import succeeds durably, when commit completes, then the local guest snapshot clears."
---

## Problem

`ST-32-04` established the browser-owned guest snapshot contract for Klassrumskartan, but the
highest-risk boundary in the public curated-app package still sits ahead: converting that
browser-owned guest snapshot into authenticated, owner-scoped planner assets without introducing
destructive merges, duplicate-heavy imports, or implicit migration behavior that violates
`ADR-0079`.

Three concrete risks make this boundary too important to leave as an implementation detail:

1. the guest snapshot can become coupled to login/registration semantics in a way that triggers
   migration too early
2. import can become destructive or duplicate-heavy if it lacks one explicit idempotent receipt
   boundary driven by snapshot identity and per-entity fingerprints
3. Klassrumskartan's planner-specific invariants, especially one-active-draft-per-kind and
   additive export-backed checkpoints, can be flattened into a generic "workspace import" that
   loses the rules already approved in `ADR-0079`

This PR therefore defines the first bounded `ST-32-05` implementation slice as a contract-first,
non-destructive authenticated guest-upgrade foundation rather than a full guest-to-account
vertical cutover.

## Goal

Land the first authenticated guest-upgrade foundation for Klassrumskartan with these properties:

- route-scoped authenticated upgrade prompting on the authenticated Klassrumskartan host
- explicit `import`, `discard`, and `postpone` user choices
- one authenticated Klassrumskartan guest-upgrade orchestration endpoint
- one receipt model shared by preview and commit
- idempotent processing based on `snapshot_id`, `snapshot_content_hash`, schema version, and
  per-entity fingerprints
- non-destructive default collision policy for rosters, templates, smart rules, drafts, and
  checkpoints
- local guest snapshot clearing only after durable success

This slice should prove the orchestration shape and conflict rules first. It should not attempt to
solve every future guest-import edge case or introduce a product-wide guest-import center.

## Non-goals

- No global post-login guest-import center across all curated apps.
- No registration-triggered migration.
- No automatic or silent import after login.
- No replacement of current active grouping or seating drafts by default.
- No broad cross-app public-import framework beyond Klassrumskartan's first consumer boundary.
- No weakening of `/apps/:appId`, `GET /api/v1/apps/{app_id}`, or the owner-scoped authenticated
  Klassrumskartan APIs.
- No full public Klassrumskartan guest-editing expansion beyond the already approved `ST-32-04`
  guest snapshot foundation.

## Locked decisions for this slice

These decisions are intentionally fixed before implementation so the slice stays bounded and
reviewable.

### 1. Prompt location

- Use a route-scoped authenticated Klassrumskartan prompt on the authenticated host.
- Do not build a global auth/bootstrap guest-import prompt in this slice.

Reasoning:

- This is the smallest safe seam.
- It matches the current curated-app architecture, where Klassrumskartan already owns its bespoke
  entry shell and authenticated host behavior.
- It avoids pulling app-specific guest-upgrade policy into global auth bootstrap too early.

### 2. API shape

- Use one authenticated Klassrumskartan guest-upgrade endpoint with `mode: "preview" | "commit"`.
- Do not split preview and commit across separate endpoints in this slice.

Reasoning:

- One endpoint keeps the orchestration boundary explicit.
- Preview and commit can share the same receipt model, conflict policy, and idempotency contract.
- This reduces drift between "what would happen" and "what did happen."

### 3. Conflict policy

- Rosters/templates: exact fingerprint match => `reused`; same-name/different-content =>
  separate non-destructive `created`
- Smart rules: dedupe by roster mapping + rules fingerprint; no destructive overwrite default
- Drafts: import as historical by default; never replace current active draft in this slice
- Checkpoints: additive import with fingerprint dedupe

Reasoning:

- These rules are the safest translation of `ADR-0079` into the current Klassrumskartan model.
- They preserve the one-active-draft-per-kind rule and avoid surprising data loss.

### 4. Guest local clearing

- `postpone` => keep local snapshot
- preview failure or commit failure => keep local snapshot
- durable commit success => clear local snapshot

Reasoning:

- This keeps the browser-owned guest state authoritative until the authenticated import is actually
  durable.
- It matches the story's explicit requirement that guest state only clears after durable success.

### 5. `task_entry_classroom_selection_mode`

- Preserve and consume it end-to-end in the authenticated import pipeline.
- Do not keep it as a known-but-ignored guest contract field.

Reasoning:

- `ST-32-04` deliberately preserved this field in the guest snapshot contract.
- Leaving it ignored would carry a known contract gap forward into the import slice.

## Why this implementation shape is recommended

This shape is recommended because it matches both the approved architecture and the repo's current
state:

- `ADR-0079` explicitly requires migration to happen only after a real authenticated session, not
  on registration, and to remain prompt-based and idempotent by default
- `ST-32-04` already established browser-owned guest snapshots, stable snapshot identity, content
  hashing, and per-entity fingerprints in the frontend contract
- the current auth model in `src/skriptoteket/web/api/v1/auth.py` still separates registration
  from login cookies, which means the first correct migration trigger is authenticated host entry
  after login, not the registration form
- the current Klassrumskartan API/application layout is already app-specific and owner-scoped, so
  the safest first upgrade seam is also app-specific rather than a new global import center
- the current draft model and planner repository protocols do not yet expose a durable
  import-identity seam for historical draft dedupe, so this slice must add one explicitly rather
  than pretending repeat-commit idempotency is already available

This plan intentionally prioritizes one honest orchestration boundary over visible breadth.
Klassrumskartan's one-active-draft-per-kind rule and additive checkpoint semantics are too easy to
damage if import policy is allowed to stay implicit.

## Implementation plan

### 1. Docs and scope lock

Create this PR document first and update `docs/index.md` so the planned slice is visible in the
docs-as-code trail before code changes begin.

### 2. Frontend route-scoped upgrade orchestration

Create a dedicated frontend guest-upgrade layer under
`frontend/apps/skriptoteket/src/views/apps/`:

- `classroomPlannerGuestUpgradeTypes.ts`
- `classroomPlannerGuestUpgradeApi.ts`
- `useClassroomPlannerGuestUpgrade.ts`
- `ClassroomPlannerGuestUpgradePrompt.vue`

Update the authenticated Klassrumskartan host entry to surface a pending guest upgrade only when:

- the current host mode is authenticated
- the local guest snapshot exists
- the snapshot profile supports upgrade
- the user has a real authenticated session

Route-scoped means this prompt belongs to Klassrumskartan's authenticated entry flow, not to a
global auth bootstrap.

### 3. Frontend integration points

Touch these existing frontend files only as needed:

- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.vue`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshot.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshotMapping.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestStorage.ts`

Responsibilities:

- expose pending upgrade state in authenticated mode
- gate authenticated planner bootstrap while a pending guest-upgrade decision is unresolved
- submit preview or commit through the new API layer
- retain browser snapshot data on `postpone` or failure
- clear browser snapshot only after durable commit success
- keep the live authenticated planner from bootstrapping until the user explicitly acts on the
  prompt or the import attempt resolves

### 4. Backend authenticated guest-upgrade API boundary

Create an authenticated Klassrumskartan guest-upgrade endpoint:

- `src/skriptoteket/web/api/v1/apps_classroom_planner_guest_upgrade.py`

Update:

- `src/skriptoteket/web/router.py`

Recommended endpoint shape:

- `POST /api/v1/apps/classroom.group-seating-studio/guest-upgrade`

Request:

- `mode: "preview" | "commit"`
- schema version
- `snapshot_id`
- `snapshot_content_hash`
- per-entity fingerprints
- full guest snapshot payload

Auth rules:

- authenticated-only
- CSRF-protected
- never public

### 5. Backend application contract and handler

Create:

- `src/skriptoteket/application/curated_apps/classroom_planner/guest_upgrade_contracts.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/handlers/guest_upgrade.py`

Update:

- `src/skriptoteket/application/curated_apps/classroom_planner/__init__.py`

Responsibilities:

- define preview/commit request DTOs
- define structured import receipts
- implement one guest-upgrade orchestration handler shared by preview and commit
- enforce non-destructive default conflict policy
- server-side recompute `snapshot_content_hash` and entity fingerprints from the submitted payload
  before any dedupe/import decision; client-submitted hashes/fingerprints are advisory only
- drive idempotent reuse decisions from server-owned snapshot identity plus recomputed entity
  fingerprints
- use one durable draft import identity / lookup seam so repeated commits do not duplicate
  historical drafts

### 6. Backend protocol seam

Create:

- `src/skriptoteket/protocols/classroom_planner_guest_upgrade.py`

Purpose:

- keep the orchestration contract protocol-first
- avoid leaking concrete repository details into the handler
- preserve a dedicated seam for future receipt persistence if later needed

This slice should prefer a dedicated guest-upgrade protocol over overloading the existing
classroom-planner repository protocols too early.

It should also add one narrow persistence seam for durable imported-draft identity / lookup rather
than claiming repeat-commit historical-draft idempotency on top of the current planner draft
protocols alone.

### 7. DI wiring

Update:

- `src/skriptoteket/di/curated_apps.py`

Responsibilities:

- register the guest-upgrade handler via Dishka
- wire any guest-upgrade-specific services/protocols
- keep the web layer thin

### 8. Minimal backend persistence touch policy

This slice should be careful about how far it pushes persistence changes.

Recommended rule:

- do not introduce broad new persistence tables unless correctness actually requires them
- always recompute `snapshot_content_hash` and per-entity fingerprints server-side from the
  submitted guest payload before dedupe/import decisions
- use snapshot identity, recomputed content hash, owner context, and recomputed per-entity
  fingerprints as the first idempotency basis
- add one explicit durable draft import identity / lookup seam for imported historical drafts; do
  not rely on active-draft or resumable-draft lookups for repeat-commit idempotency
- if durable receipt or import-identity persistence is required, keep it behind one explicit
  guest-upgrade protocol and one small repository seam, not spread across planner repositories

### 9. Entity-specific import policy for this slice

Rosters:

- exact fingerprint match under the authenticated owner => `reused`
- same name but different fingerprint => `created` separately

Templates:

- exact fingerprint match under the authenticated owner => `reused`
- same name but different fingerprint => `created` separately

Smart rules:

- dedupe by imported/reused roster mapping plus rules fingerprint
- no destructive overwrite default

Drafts:

- import guest grouping/seating drafts as historical by default
- never replace the current active draft in this slice
- preserve one-active-draft-per-kind invariants

Checkpoints:

- additive import with fingerprint dedupe
- never replace existing history by default

### 10. `task_entry_classroom_selection_mode`

This field was intentionally preserved into the `ST-32-04` guest snapshot contract and should be
consumed in this slice, not silently carried forever.

This slice should therefore:

- accept it in the guest snapshot payload
- carry it through draft import decisions or imported draft metadata
- include it in the receipt or imported-draft construction path where relevant

## Files expected to change

Create:

- `docs/backlog/prs/pr-0221-st-32-05-authenticated-upgrade-orchestration-and-idempotent-import-policy-foundation.md`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestUpgradeTypes.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestUpgradeApi.ts`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestUpgrade.ts`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestUpgradePrompt.vue`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestUpgradeApi.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestUpgrade.spec.ts`
- `src/skriptoteket/web/api/v1/apps_classroom_planner_guest_upgrade.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/guest_upgrade_contracts.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/handlers/guest_upgrade.py`
- `src/skriptoteket/protocols/classroom_planner_guest_upgrade.py`
- `tests/unit/web/test_apps_classroom_planner_guest_upgrade.py`
- `tests/unit/application/curated_apps/classroom_planner/test_classroom_planner_guest_upgrade_handler.py`

Update:

- `docs/index.md`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.vue`
- `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.spec.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshot.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestSnapshotMapping.ts`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestStorage.ts`
- `src/skriptoteket/web/router.py`
- `src/skriptoteket/application/curated_apps/classroom_planner/__init__.py`
- `src/skriptoteket/di/curated_apps.py`

Only update existing planner repository protocols or infrastructure repositories if the handler
cannot stay correct without one narrowly scoped helper seam.

For this slice, a narrow helper seam for durable draft import identity / lookup is considered in
scope because the current draft model/repository surface is not sufficient to make the stronger
repeat-commit idempotency claim honest.

## PR-sized execution checklist

- [ ] Add this PR document and update `docs/index.md`
- [ ] Add typed frontend guest-upgrade DTOs and API client
- [ ] Add authenticated Klassrumskartan guest-upgrade prompt orchestration that gates planner
      bootstrap while the decision is unresolved
- [ ] Add authenticated guest-upgrade API route with `preview|commit`
- [ ] Add application-layer guest-upgrade contracts and handler
- [ ] Add server-side recomputation of snapshot content hash and per-entity fingerprints before
      dedupe/import decisions
- [ ] Add one narrow durable draft import identity / lookup seam for historical draft idempotency
- [ ] Add Dishka wiring for the guest-upgrade handler
- [ ] Preserve and consume `task_entry_classroom_selection_mode` in the import path
- [ ] Add targeted backend tests for preview, commit, idempotency, conflict policy, auth/CSRF
      negatives, and registration-without-session no-op behavior
- [ ] Add targeted frontend tests for prompt behavior and local-clear policy
- [ ] Run targeted verification and record it in `.agents/handoff.md`
- [ ] Run independent `skriptoteket_reviewer` on the implemented slice before close-out

## Test plan

Backend:

- `pdm run pytest tests/unit/web/test_apps_classroom_planner_guest_upgrade.py tests/unit/application/curated_apps/classroom_planner/test_classroom_planner_guest_upgrade_handler.py`
- backend verification must explicitly cover:
  - unauthenticated request rejected
  - missing/invalid CSRF rejected
  - registration without authenticated session does not trigger guest upgrade
  - server-side recomputation overrides mismatched client-submitted hash/fingerprint values
  - repeat commit reuses historical draft import identity instead of duplicating drafts

Frontend:

- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/useClassroomPlannerGuestUpgrade.spec.ts src/views/apps/classroomPlannerGuestUpgradeApi.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

Docs:

- `pdm run docs-validate`

Live functional check if UI/route behavior changes:

- verify authenticated route remains the authenticated host:
  - `http://127.0.0.1:5173/apps/classroom.group-seating-studio`
- verify public route still preserves browser snapshot continuity:
  - `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
- verify authenticated upgrade prompt behavior:
  - pending guest snapshot + login => prompt shown before planner bootstrap
  - `postpone` => snapshot retained
  - `discard` => snapshot cleared locally with no import
  - `commit` success => snapshot cleared after success receipt only

## Rollback plan

- Revert the guest-upgrade prompt, API route, handler, and DTOs together if the import policy is
  found to violate non-destructive defaults.
- Do not keep a half-landed prompt that can offer import without a correct authenticated
  orchestration boundary.
- Do not fall back to registration-triggered migration or implicit login-time import.
- Preserve the docs trail so later `ST-32-05` and `ST-32-06` work still starts from the reviewed
  contract and conflict policy.
