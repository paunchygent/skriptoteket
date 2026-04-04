---
type: pr
id: PR-0211
title: "ST-32-04 Option A1: guest snapshot frontend hardening"
status: ready
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-32-04"
tags: ["frontend", "klassrumskartan", "public-host", "guest-storage", "review-fixes"]
dependencies:
  - "EPIC-32"
  - "ADR-0079"
acceptance_criteria:
  - "Given the authenticated host mode does not use the browser-owned guest workspace flow, when the guest snapshot status composable is created with `enabled: false`, then no guest storage adapter is constructed or bound."
  - "Given guest snapshots must support later dedupe and import receipts, when guest fingerprints and content hashes are generated, then they use a deterministic algorithm with materially wider output than the previous 32-bit scheme and remain stable across object key ordering."
  - "Given local browser state can drift, when the current pointer references a missing snapshot record but another valid guest snapshot still exists in IndexedDB, then the guest storage adapter repairs the pointer to the most recent valid snapshot instead of reporting a false missing state."
  - "Given the public entry shell surfaces guest snapshot status, when focused view tests run, then loading, error, expired, missing, and ready states remain explicit without affecting the authenticated host path."
  - "Given this is a reviewed bounded fix slice, when implementation is complete, then scope remains limited to the ST-32-04 Option A1 frontend guest snapshot files and focused tests."
---

## Problem

The reviewed ST-32-04 Option A1 slice landed the browser-owned guest snapshot
foundation, but three follow-up risks remained:

1. the guest storage adapter was still constructed eagerly even when the
   authenticated host path disabled guest mode
2. the initial fingerprint/content-hash helper used a narrow 32-bit hash that
   is not strong enough for future dedupe and import receipt workflows
3. guest storage and entry-shell tests did not yet prove the disabled path,
   pointer-repair behavior, or the remaining public-shell status surfaces

## Goal

Harden the bounded guest snapshot foundation so the public shell stays honest,
the authenticated shell avoids unused guest storage wiring, and snapshot
identity is strong enough for later ST-32-05 import/idempotency work.

## Non-goals

- No expansion into authenticated import orchestration or migration UX.
- No backend/API changes.
- No broader public host redesign outside the current guest snapshot seam.
- No changes outside the reviewed Option A1 frontend files except required docs
  governance updates.

## Implementation plan

1. Make `useClassroomPlannerGuestSnapshotStatus` resolve guest storage lazily so
   `enabled: false` does not construct the adapter.
2. Replace the 32-bit hash helper with a deterministic SHA-256 digest over the
   existing stable stringification format.
3. Extend guest storage pointer recovery so an orphaned current pointer can
   repair itself to the latest valid stored snapshot.
4. Add focused Vitest coverage for lazy construction, digest stability/format,
   pointer repair, and entry-shell loading/error/expired evidence.
5. Record verification and reviewer outcomes in this PR doc before close-out.

## Test plan

- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/classroomPlannerGuestStorage.spec.ts src/views/apps/classroomPlannerGuestSnapshotMapping.spec.ts src/views/apps/classroomPlannerGuestFingerprint.spec.ts src/views/apps/useClassroomPlannerGuestSnapshotStatus.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- focused public-shell smoke against `http://127.0.0.1:5173` if the local app is available

## Implementation Summary (as of 2026-04-04)

- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestStorage.ts` now supports
  orphaned-pointer repair by selecting the most recently updated non-expired guest snapshot from
  IndexedDB before falling back to `missing`
- `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestFingerprint.ts` now emits
  deterministic `sha256:<hex>` digests for both per-entity fingerprints and snapshot content hashes
- focused coverage now exists for:
  - lazy disabled guest-storage construction in
    `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestSnapshotStatus.spec.ts`
  - digest determinism, key-order stability, and widened format in
    `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestFingerprint.spec.ts`
  - orphaned pointer repair in
    `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestStorage.spec.ts`
  - loading/error/expired public-shell evidence in
    `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerEntryView.spec.ts`
- `docs/index.md` now links this missing PR-slice artifact so the EPIC-32 docs trail is complete

## Verification Notes (2026-04-04)

- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/classroomPlannerGuestStorage.spec.ts src/views/apps/classroomPlannerGuestSnapshotMapping.spec.ts src/views/apps/classroomPlannerGuestFingerprint.spec.ts src/views/apps/useClassroomPlannerGuestSnapshotStatus.spec.ts`
  - pass; `5` files, `21` tests
- `pdm run docs-validate`
  - pass
- `pdm run fe-type-check`
  - blocked by unrelated pre-existing local error in
    `frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy/game/physics/__tests__/PhysicsWorld.launcher.spec.ts`
    (`TS2307: Cannot find module 'node:fs/promises'`)
- live public-shell proof via Playwright MCP:
  - navigated to `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
  - observed `Klassrumskartan` public host shell rendering with the missing guest-workspace state
    and `Initiera lokal gästarbetsyta` CTA

## Reviewer Notes

- first sole-reviewer pass found two docs-trail issues:
  - stale PR path in `docs/index.md` and `.agents/handoff.md`
  - stale digest-format note in `.agents/handoff.md`
- both findings were fixed in-slice and `pdm run docs-validate` was rerun successfully
- second and final sole-reviewer pass returned no actionable findings

## Rollback plan

Revert only the guest snapshot frontend hardening in this slice, restoring the
previous eager storage wiring and fingerprint helper if a regression appears,
while preserving the broader ST-32-04 public-host foundation.
