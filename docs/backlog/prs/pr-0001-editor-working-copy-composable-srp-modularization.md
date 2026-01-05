---
type: pr
id: PR-0001
title: "Refactor: split useEditorWorkingCopy into focused modules (SRP)"
status: ready
owners: "agents"
created: 2026-01-05
updated: 2026-01-05
stories:
  - "ST-14-30"
adrs:
  - "ADR-0027"
tags: ["frontend", "editor", "refactor", "srp"]
acceptance_criteria:
  - "useEditorWorkingCopy keeps the same exported API (no call-site changes outside the editor folder)."
  - "Behavior is unchanged: working-copy head persistence, checkpoint behavior, restore flows, and warning/toast semantics remain identical."
  - "useEditorWorkingCopy.ts is reduced below the repo size budget (<500 LOC) by extracting cohesive modules."
  - "Unit tests pass (at minimum: pdm run fe-test, pdm run fe-type-check)."
  - "A basic editor live check is done (start Vite + open editor view) and recorded in .agent/handoff.md."
---

## Problem

`frontend/apps/skriptoteket/src/composables/editor/useEditorWorkingCopy.ts` currently mixes:

- IndexedDB persistence concerns (heads + checkpoints + TTL trimming)
- Editor-state orchestration (dirty tracking, autosave cadence, transitions)
- Restore candidate UX semantics (prompt visibility + “stash on edit”)
- Error/toast policy (warn-once behavior)
- Convenience helpers (labels, timestamps, fingerprints)

This makes it harder to reason about correctness in the editor feature chain (save → diff → AI apply/chat), and it
is already over the file size budget.

## Goal

Extract cohesive modules to restore SRP boundaries while keeping the public composable API stable and minimizing churn.

## Non-goals

- No behavior changes, new UI, or new persistence semantics.
- No cross-folder “architecture refactor” (keep everything within the editor composables area).

## Proposed refactor order (minimize churn)

1) **Extract pure helpers first (no behavior change)**

   - New file(s) for timestamp/TTL helpers, labels, and fingerprinting.
   - Keep all existing unit tests passing throughout.

2) **Extract persistence primitives**

   - New module for “head” persistence (load/save/clear + TTL purge).
   - New module for checkpoints (list/create/trim/clear + pinned vs auto policy).
   - Both modules remain thin wrappers over `editorPersistence.ts` so the IndexedDB schema stays centralized.

3) **Extract restore-candidate policy**

   - Move “restore candidate lifecycle” + “stash on first edit” rules into a dedicated module.
   - Keep the orchestration in `useEditorWorkingCopy.ts`, but delegate decisions + side effects.

4) **Keep useEditorWorkingCopy as the orchestrator**

   - `useEditorWorkingCopy.ts` becomes the “wiring” file: connects editor buffers, persistence modules, and notifications.
   - Avoid moving exports/types unless required; keep return shape and function names intact.

## Implementation notes

- Prefer small modules under `frontend/apps/skriptoteket/src/composables/editor/` with narrow responsibilities.
- Keep all names aligned with existing domain language: “working copy head”, “checkpoint”, “restore candidate”.
- Use dependency-injection patterns already in place (don’t couple to concrete storage).

## Test plan

- `pdm run fe-test`
- `pdm run fe-type-check`
- Optional (recommended): `pdm run ui-editor-smoke` (may require escalation on macOS; store artifacts under `.artifacts/`).

## Rollback plan

- Revert by reverting the PR commit(s); no migrations or schema changes expected.
