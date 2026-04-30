---
type: story
id: ST-32-04
title: "Browser-owned guest-state profiles and snapshot contracts"
status: done
owners: "agents"
created: 2026-04-03
updated: 2026-04-30
epic: "EPIC-32"
dependencies: ["ST-32-01", "ST-32-02", "ST-32-03", "ADR-0079"]
acceptance_criteria:
  - "Given a curated app uses a browser-owned public profile, when its guest-state contract is defined, then the browser is the authoritative store and the server does not create owner-scoped guest workspace rows before login."
  - "Given browser-owned guest persistence is reviewed, when storage semantics are documented, then IndexedDB/localStorage responsibilities, TTL/reset behavior, cross-tab expectations, and privacy notice requirements are explicit."
  - "Given guest-state semantics differ across access profiles, when the contract is reviewed, then `public_stateless`, `public_browser_runtime`, and `public_browser_workspace_with_upgrade` have distinct persistence expectations rather than one overloaded guest-storage model."
  - "Given Klassrumskartan uses guest-local history concepts, when its snapshot shape is defined, then the plan distinguishes undo/redo, local draft/history continuity, and export-backed checkpoints instead of collapsing them into one generic history field."
  - "Given guest-to-account upgrade must be idempotent later, when the snapshot contract is defined, then it includes schema versioning, a stable snapshot identity or content hash, and per-entity fingerprints for migratable assets."
ui_impact: "Guest/public curated-app UX gains explicit local-storage, expiry, and reset semantics."
data_impact: "Browser storage contract only; no new server-owned guest tables are assumed."
---

## Context

Klassrumskartan's guest demo requirement is not just “let unauthenticated users
through the door.” It needs browser-owned rosters, templates, drafts, and
history semantics that can later become authenticated assets without first
living in account tables.

## Notes

- This story defines the cross-app profile rules and the Klassrumskartan-style
  snapshot contract they enable.
- Guest browser storage must be treated as privacy-sensitive when names or
  classroom data can be present.
- Export-backed checkpoints remain intentionally separate from undo/redo and
  local draft restore semantics.
- Snapshot identity must be strong enough to support dedupe, retry safety, and
  authenticated import receipts later.

## Status Reconciliation (2026-04-30)

This story is now marked `done`. The indexed `PR-0211` Option A1 record
documents the delivered browser-owned guest snapshot storage, lazy public-only
storage construction, orphaned-pointer repair, and `sha256:` fingerprint/hash
contract used by later authenticated upgrade and public workspace slices.
