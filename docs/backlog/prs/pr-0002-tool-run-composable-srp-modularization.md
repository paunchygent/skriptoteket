---
type: pr
id: PR-0002
title: "Refactor: split useToolRun into focused modules (SRP)"
status: done
owners: "agents"
created: 2026-01-05
updated: 2026-01-05
stories:
  - "ST-12-04"
  - "ST-12-07"
tags: ["frontend", "tool-run", "refactor", "srp"]
acceptance_criteria:
  - "useToolRun keeps the same exported API (no call-site changes outside its own folder)."
  - "Behavior is unchanged: request payload construction, polling cadence, cancellation/cleanup, and error handling remain identical."
  - "At least one cohesive sub-module is extracted (polling and/or session-files manager), reducing the responsibilities of useToolRun.ts."
  - "Frontend checks pass (at minimum: pdm run fe-test, pdm run fe-type-check, pdm run fe-lint)."
---

## Problem

`frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts` carries multiple responsibilities that have grown
over several stories (inputs, file upload, session file reuse/clear, sandbox contexts, and polling).

This increases risk and slows iteration for upcoming tool-run enhancements and editor-adjacent work, because changes
to one concern (e.g. session file reuse) easily cause regressions in another (e.g. polling state or request building).

## Goal

Extract cohesive modules while keeping the public `useToolRun` API stable and minimizing churn.

## Non-goals

- No API contract changes to backend endpoints.
- No UI changes beyond what’s required for extraction.

## Proposed refactor outline (keep API stable)

1) **Extract polling**

   - New module: `useToolRunPolling` that owns timers, backoff/cadence rules, cancellation, and cleanup.
   - `useToolRun` delegates polling concerns but keeps the same returned state/actions.

2) **Extract session-files manager**

   - New module: `useToolSessionFiles` that owns list/refresh/clear/reuse semantics and `session_context` derivation.
   - Consolidate the “reuse/clear/none” branching to a single place (ST-12-07).

3) **Extract request building**

   - New module: `toolRunRequest` (or similar) that builds `FormData` consistently for:
     - `inputs` JSON
     - optional `files[]`
     - optional session file mode/context

4) **Leave useToolRun as the façade**

   - Keep the same function signature and returned API.
   - Keep call sites unchanged; prefer internal-only module boundaries.

## Test plan

- `pdm run fe-test`
- `pdm run fe-type-check`
- `pdm run fe-lint`

## Rollback plan

- Revert by reverting the PR commit(s); no migrations expected.
