---
type: pr
id: PR-0222
title: "ST-32-06: browser-authored guest checkpoint payload capture for export-backed history"
status: canceled
owners: "agents"
created: 2026-04-04
updated: 2026-04-04
stories:
  - "ST-32-06"
tags: ["frontend", "klassrumskartan", "guest-history", "guest-export", "public-access"]
dependencies:
  - "ADR-0079"
  - "ST-32-04"
  - "ST-32-05"
  - "EPIC-27"
acceptance_criteria:
  - "Given browser-authored guest snapshots already serialize canonical checkpoint payloads, when `PR-0221` no longer needs legacy compatibility support, then the stale follow-up planning lane is canceled instead of left as an implicit future obligation."
  - "Given no non-developer legacy guest snapshots remain in scope, when authenticated guest-upgrade validates checkpoint payloads, then metadata-only checkpoint payloads are rejected rather than supported via `skipped` fallback behavior."
---

## Problem

This PR was created when the repo still carried an explicit temporary plan to
support metadata-only legacy guest checkpoints via `skipped` fallback behavior
until the browser-authored checkpoint writer path was confirmed.

That follow-up is now stale. The current browser-owned guest snapshot contract
already carries canonical checkpoint payload fields, the authenticated importer
already consumes those fields, and there are no non-developer legacy snapshots
that justify keeping dead compatibility seams alive.

## Resolution

Cancel this PR as obsolete planning and keep the simpler current policy:

- browser-authored guest snapshots must send canonical checkpoint payloads
- authenticated guest-upgrade rejects metadata-only checkpoint payloads
- Klassrumskartan should not preserve dead legacy-compatibility code solely for
  developer-owned snapshots that no longer exist

## Notes

- The remaining `PR-0221` repeat-commit idempotency proof is already covered in
  `tests/unit/application/apps/classroom_planner/test_guest_upgrade_idempotency.py`.
- If a future migration ever truly needs metadata-only checkpoint support
  again, it should be reintroduced only through a new explicit story/PR decision
  rather than by reviving this canceled planning stub implicitly.
