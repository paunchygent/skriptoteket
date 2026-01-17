---
type: pr
id: PR-0036
title: "Editor AI: layered diff validation + hunk repair for edit-ops"
status: ready
owners: "agents"
created: 2026-01-17
updated: 2026-01-17
stories:
  - "ST-08-29"
tags: ["backend", "editor", "ai", "protocol"]
acceptance_criteria:
  - "Preview accepts patch ops that contain bare `@@` hunk separators or missing hunk ranges by repairing headers against the base file."
  - "Patch ops with no valid hunks and no repairable context fail fast with a clear regenerate error (no apply attempt)."
  - "Structured output constraints remain JSON-only; diff semantic validation happens in preview/apply."
  - "Verification: `pdm run test` (or targeted unit tests for the diff applier)."
---

## Problem

Fallback models can return JSON-shaped patch ops whose `patch_lines` contain invalid unified diff syntax (e.g. bare `@@`
lines or missing hunk ranges). The JSON schema passes, but preview/apply fails with `patch_prepare_failed`, forcing
regeneration even when the edit is otherwise correct.

## Goal

- Implement a layered diff pipeline that repairs missing hunk ranges when possible.
- Keep strict atomic apply and bounded fuzz, while avoiding unnecessary regeneration for recoverable diffs.
- Document the new behavior in ADR-0051.

## Non-goals

- Changing the patch-only protocol or introducing structured hunk schemas.
- UI changes to the diff panel.
- Changing the model prompt (no new prompt instructions required).

## Implementation plan

1. Extend the unified diff applier to:
   - Strip apply-patch wrappers (`*** Begin Patch`, `*** Update File`, etc.).
   - Detect diff shape (valid hunks vs bare/missing hunk ranges).
   - Repair missing hunk headers by anchoring against the base file.
2. Relax patch-op validation to allow missing `@@` headers so repair can run.
3. Update preview to pass base text into diff preparation (for hunk repair).
4. Add unit tests for:
   - bare `@@` repair,
   - missing hunk header synthesis,
   - and normal apply behavior.
5. Update ADR-0051 and docs index.

## Test plan

- `pdm run test` (or `pdm run test -k unified_diff_applier`)

## Rollback plan

- Revert this PR. Preview/apply will return to strict “valid hunk headers required.”
