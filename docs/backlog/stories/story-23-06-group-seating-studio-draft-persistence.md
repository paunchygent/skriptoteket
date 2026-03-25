---
type: story
id: ST-23-06
title: "Klassrumskartan — PlanDraft Persistence and Autosave"
status: done
owners: "agents"
created: 2026-03-20
updated: 2026-03-25
epic: "EPIC-23"
acceptance_criteria:
  - "Given an active draft, when an assignment reducer fires, then a background XHR PATCH request silently saves the draft state."
  - "Given a page reload, when the user returns to an incomplete draft, then the exact group and seat assignments are restored."
---

## Context
With the frontend normalized state strictly managing interactions, this story introduces the actual auto-save syncing to the relational database `PlanDraft` entity.

## Implementation Plan

### [ ] PR 1: Backend Draft Endpoints
- **Intent**: Provide `POST /drafts` and `PATCH /drafts/{id}` logic.
- **Code Choice**: App-specific relational `PlanDraft` table with versioning/optimistic revision fields. Handlers should accept partial patches mapping to the `GroupAssignment` and `SeatAssignment` subsets.

### [ ] PR 2: Frontend Autosave Sync
- **Intent**: Reactively trigger debounced patches.
- **Code Choice**: Wire a watcher/subscriber in `useClassroomState.ts` that listens for any state reducer mutation and triggers a background API `PATCH` ensuring durable Draft continuity.

## Implementation Summary (as of 2026-03-25)

- Draft persistence shipped beyond the initial minimal autosave concept and now survives reloads through authoritative backend-owned draft state.
- The planner uses optimistic revision handling plus background save/reload flows instead of treating classroom work as ephemeral client-only state.
- Later class-first continuity and history work in `EPIC-24` extends this shipped draft seam rather than introducing a separate persistence model.
