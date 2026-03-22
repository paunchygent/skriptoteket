---
type: pr
id: PR-0090
title: "Klassrumskartan: grouping draft-history contract"
status: ready
owners: "agents"
created: 2026-03-22
updated: 2026-03-22
stories:
  - "ST-24-03"
tags: ["backend", "api", "persistence"]
acceptance_criteria:
  - "Grouping drafts keep bounded recent history as part of draft working state so undo and redo can be supported without creating separate saved items."
  - "The recent-history depth is configurable, with the current planning target set to 10 steps."
  - "Grouping draft payloads and history entries stay grouping-focused and do not revive seating-only or whole-workspace snapshot semantics."
  - "Backend contracts support autosave progression plus undo/redo navigation for the active grouping draft without introducing a separate saved-artifact hierarchy."
  - "Backend tests cover history bounds, undo/redo state transitions, and class-scoped draft continuity."
---

## Problem

`ST-24-02` established class-first entry and clean draft-kind lifecycle, but grouping still lacks
the backend contract needed for bounded draft history inside one active draft. Without that
contract, frontend undo/redo behavior would either be guessed client-side or would drift toward a
confusing separate saved-item model.

## Goal

Add the backend/domain contract for grouping draft history as operational working state:

- one active grouping draft remains authoritative
- autosave keeps the draft current
- bounded recent history supports undo/redo
- recent history stays part of the draft, not a file-vault or named-artifact concept

## Non-goals

- Grouping board UI changes such as `Slumpa`, group-card layout fixes, or draft-entry controls.
- Export generation (PDF/XLSX) or file-vault projection.
- Seating draft-history persistence from `ST-24-04`.
- Exposing technical history as a separate saved-items archive.

## Checklist

- [ ] Add a bounded grouping draft-history contract aligned with `ST-24-03`.
- [ ] Keep autosave semantics separate from any later export or checkpoint semantics.
- [ ] Make recent-history depth configurable, with 10 as the initial target.
- [ ] Support undo and redo navigation against the active grouping draft.
- [ ] Keep grouping history payloads focused on grouping data and grouping-relevant context only.
- [ ] Add backend tests for history bounds, undo/redo transitions, and class-scoped draft continuity.

## Implementation plan

- Add domain/application models for grouping draft-history entries or patches that remain internal
  to the active grouping draft.
- Persist a bounded recent-history buffer alongside the active draft so newer changes evict older
  ones once the configured limit is reached.
- Add handlers and repository protocol methods for:
  - append recent history entry on meaningful grouping change
  - step undo on the active grouping draft
  - step redo on the active grouping draft
  - report history availability compactly to the frontend
- Keep the contract class-scoped and draft-kind-aware so grouped history never drifts back toward
  owner-global semantics.

## Test plan

- Backend:
  - recent-history entries are appended for grouping changes
  - undo and redo move the active draft state correctly
  - history remains bounded at the configured depth
  - grouping history payloads do not leak seating-only fields
- Manual:
  - hit the grouping draft-history endpoints/handlers and confirm the contract distinguishes one
    active draft with history from any notion of separate saved items

## Rollback plan

- Revert the grouping draft-history persistence and API additions if they produce unstable working
  state, while keeping the `ST-24-02` class-first draft-kind flow intact.

## Follow-up direction

- `PR-0091` completes the live grouping workspace fundamentals that will consume this contract.
- `PR-0092` wires teacher-facing undo/redo and autosave feedback on top of the draft-history
  contract.
