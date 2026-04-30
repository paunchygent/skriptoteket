---
type: pr
id: PR-0211
title: "ST-32-04: browser-owned guest snapshot contract and storage foundation"
status: canceled
owners: "agents"
created: 2026-04-04
updated: 2026-04-30
stories:
  - "ST-32-04"
tags: ["frontend", "klassrumskartan", "guest-state", "public-access"]
dependencies:
  - "ADR-0079"
  - "ST-32-01"
  - "ST-32-02"
  - "ST-32-03"
acceptance_criteria:
  - "Given Klassrumskartan uses the approved `public_browser_workspace_with_upgrade` profile, when the browser-owned guest contract is inspected, then it has schema versioning, stable snapshot identity/content hashing, and per-entity fingerprints for migratable assets."
  - "Given the public host reads guest snapshot status, when the authenticated host is mounted, then it does not eagerly bind browser-owned guest storage or depend on local browser globals."
  - "Given the browser owns guest persistence in this slice, when IndexedDB/localStorage state is inspected, then the current pointer, TTL expiry, reset behavior, and orphaned-pointer repair are explicit and tested."
  - "Given the public entry shell exposes the guest snapshot seam, when the shell is rendered, then missing, loading, ready, expired, and error states are all directly evidenced in frontend tests."
---

## Problem

`ST-32-04` needs the guest-state contract and browser-owned storage seam in place before later
guest editing and authenticated upgrade/import flows can land safely. The first implementation
pass established the basic snapshot/storage shape, but review found two boundary issues:

- the authenticated host still eagerly instantiated the public guest-storage adapter
- guest fingerprints/content hashes were too narrow for later dedupe/import-receipt safety

The public shell test coverage also needed broader direct evidence for shell states and orphaned
pointer repair.

## Status Reconciliation (2026-04-30)

This draft is canceled as an unindexed duplicate of the retained `PR-0211`
Option A1 implementation record:
`pr-0211-st-32-04-option-a1-guest-snapshot-frontend-hardening.md`. The
delivered state and verification belong there; this file should not be treated
as an open implementation task.

## Goal

Land the bounded `Option A1` foundation slice for `ST-32-04` with:

- versioned guest snapshot contract
- browser-owned storage seam
- lazy public-only storage construction
- materially wider deterministic digest contract
- direct frontend evidence for the public shell and storage repair paths

## Non-goals

- Full public Klassrumskartan guest editing.
- Authenticated import orchestration or idempotent import receipts.
- Backend-owned guest persistence.
- Broad public support for every curated app.
- Changing the authenticated `/apps/:appId` host or owner-scoped APIs.

## Implementation plan

1. Define the browser-owned guest snapshot contract and storage profile semantics for
   Klassrumskartan.
2. Persist guest snapshots in IndexedDB with only the current-pointer metadata in localStorage.
3. Keep guest storage lazy so authenticated host setup never binds browser-only storage.
4. Use deterministic wide digests for snapshot content hashes and per-entity fingerprints.
5. Prove missing/loading/ready/expired/error public-shell states and orphaned-pointer repair in
   focused Vitest coverage.

## Test plan

- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerEntryView.spec.ts src/views/apps/useClassroomPlannerGuestSnapshotStatus.spec.ts`
- `pdm run fe-test -- --run src/views/apps/classroomPlannerGuestFingerprint.spec.ts src/views/apps/classroomPlannerGuestSnapshotMapping.spec.ts src/views/apps/classroomPlannerGuestStorage.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`

## Rollback plan

- Revert the guest snapshot foundation files together if the public guest contract is wrong.
- Do not fall back to eager browser-storage binding in the authenticated lane.
- Preserve the story/ADR trail so later guest import work still starts from the reviewed
  browser-owned boundary.
