---
type: pr
id: PR-0014
title: "Editor: AI proposed changes diff preview + apply/undo (ST-08-22)"
status: ready
owners: "agents"
created: 2026-01-09
updated: 2026-01-09
stories:
  - "ST-08-22"
adrs:
  - "ADR-0051"
  - "ADR-0052"
tags: ["frontend", "editor", "ai", "diff"]
acceptance_criteria:
  - "Proposals render a per-file diff preview (current vs proposed) using the canonical virtual file map."
  - "Apply is blocked when targeted files have stale fingerprints or the draft is locked by another user."
  - "Apply creates a labeled checkpoint immediately before applying (e.g., \"Före AI-ändring\")."
  - "Apply is atomic across files and supports a single undo if no subsequent edits are made."
  - "If edits occur after apply, undo is disabled and the UI points to checkpoint restore."
  - "Discard clears the proposal without altering editor content."
---

## Problem

Structured edit-ops (ST-08-21) exist but there is no safe preview/apply UX. Without diffs, atomic apply, and undo,
the chat-first editing workflow is incomplete and risks surprising users.

## Goal

Introduce a proposal workflow that previews changes via the existing diff viewer, applies them safely with a checkpoint,
and provides a reliable undo path when no additional edits have occurred.

## Non-goals

- No new backend endpoints or persistence tables.
- No multi-range/pattern-based targeting (v1 ops only).
- No UI changes to the chat drawer beyond proposal integration.

## Open questions / decisions

### Preview computation

- Option A: Pure helper applies ops to virtual files (client-side).
  - Pros: deterministic, testable, supports preview + apply, no new endpoints.
  - Cons: must validate selection/cursor targeting.
- Option B: Backend computes diff.
  - Pros: centralizes logic.
  - Cons: new endpoints, out of scope.

**Decision:** Option A. Implement a pure helper (e.g. `applyEditOpsToVirtualFiles`) and reuse it for preview + apply.

### Proposal surface

- Option A: Main editor column panel.
  - Pros: more space, reuses diff viewer UX, consistent with ST-14-17.
  - Cons: adds another panel state.
- Option B: Chat drawer panel.
  - Pros: all in one place.
  - Cons: cramped for multi-file diffs.
- Option C: Modal.
  - Pros: focused.
  - Cons: awkward for large diffs; more a11y surface.

**Decision:** Option A (main editor column panel).

### Selection/cursor ops resolution

- Option A: Support selection/cursor only when resolvable in the active file.
- Option B: Treat unresolved selection/cursor as invalid and require regenerate.

**Decision:** Option B for v1 (safety-first).

## Implementation plan

1) **Composable + state**
   - Add `useEditorEditOps` with proposal state, stale detection (SHA-256), apply/undo helpers, and error states.
   - Keep `useEditorChat` focused on streaming text (no proposal logic).
   - Wire a chat drawer CTA that calls `/api/v1/editor/edit-ops` (non-streaming) without replacing the
     existing `/chat` SSE path.

2) **Pure ops application helper**
   - Implement `applyEditOpsToVirtualFiles(virtualFiles, ops, selection, cursor)`:
     - validates op schema and target resolution
     - returns `{ nextFiles, errors }`
   - Use it for both preview and apply to avoid divergence.

3) **Preview UI**
   - Add a “Proposed changes” panel in the main editor column.
   - Reuse diff viewer with per-file tabs for targeted files.
   - Show stale/invalid warnings and a Regenerate CTA when apply is blocked.

4) **Apply + undo**
   - On apply:
     - create checkpoint (“Före AI-ändring”)
     - apply changes atomically to all virtual files
   - Undo available only if no subsequent edits; otherwise disable and point to checkpoints.

5) **Guardrails**
   - Block apply if:
     - draft lock is held by another user
     - fingerprint mismatch on any targeted file
   - Show “Regenerate” CTA when stale/invalid.

6) **Session rule**
   - Run live UI check (backend + Vite) and record in `.agent/handoff.md`.

## Test plan

- Unit tests for `applyEditOpsToVirtualFiles(...)`.
- Unit tests for `useEditorEditOps` state transitions (proposal set/reset, stale detection, undo availability).
- Manual live check: request proposal → preview → apply → undo; record in `.agent/handoff.md`.

## Rollback plan

Revert the PR. No migrations or data changes are introduced.
