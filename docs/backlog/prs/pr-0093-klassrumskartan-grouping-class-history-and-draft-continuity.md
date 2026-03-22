---
type: pr
id: PR-0093
title: "Klassrumskartan: grouping class history and draft continuity"
status: ready
owners: "agents"
created: 2026-03-22
updated: 2026-03-22
stories:
  - "ST-24-03"
tags: ["frontend", "backend", "integration"]
acceptance_criteria:
  - "Creating a new grouping draft starts blank and demotes the previous active grouping draft to secondary class history automatically."
  - "Resuming the current grouping draft stays distinct from reopening an older superseded grouping draft."
  - "Any class-level grouping history remains clearly secondary to the active draft and its in-workspace undo/redo history."
  - "Live browser verification covers grouping draft creation, grouping randomize/manual edits, undo/redo, leaving and resuming the draft, and opening an older grouping draft from secondary history."
---

## Problem

`ST-24-03` still needs one more lifecycle polish layer after grouping fundamentals and undo/redo:

- new grouping drafts must start cleanly
- previous active grouping drafts must demote to secondary class history automatically
- class-level history must not compete with the active draft or with in-workspace undo/redo

Without this distinction, the app risks showing too many "histories" at once and becoming muddy
again.

## Goal

Finish the grouping draft workflow as a clear document-like model:

- one active grouping draft
- bounded in-workspace undo/redo for recent steps
- secondary class-level history for earlier superseded drafts

## Non-goals

- Durable export/file-vault artifact projection.
- Seating draft continuity.
- Broad archival/version-management UX.

## Checklist

- [ ] Keep `Nytt grupputkast` blank and explicit.
- [ ] Demote the previous active grouping draft to secondary class history automatically.
- [ ] Keep active-draft resume distinct from reopening an older superseded draft.
- [ ] Keep class-level grouping history secondary to the active workspace.
- [ ] Extend live browser checks for grouping draft continuity and class history behavior.

## Implementation plan

- Reuse the class-first workspace and grouping drawer patterns from `ST-24-02`, but keep prior
  grouping drafts visually secondary to the active draft.
- Distinguish clearly between:
  - current active grouping draft
  - earlier superseded grouping drafts
  - in-workspace undo/redo history
- Ensure creating a new grouping draft does not silently copy the current one.
- Keep reopening earlier grouping drafts simple and class-scoped without turning them into
  teacher-facing "saved files".

## Test plan

- Backend/integration:
  - creating a new grouping draft supersedes the previous active grouping draft
  - reopening an older grouping draft restores it as the active draft for that class
- Frontend/manual:
  - active draft remains primary
  - older drafts stay secondary
- Live/browser:
  - use the app-specific Playwright baseline to create/open grouping, make several edits, use
    undo/redo, create a blank new draft, and reopen the previous grouping draft from secondary
    class history

## Rollback plan

- Revert the class-history continuity changes if they make grouping history louder than the active
  workspace, while keeping grouping fundamentals and undo/redo intact.

## Follow-up direction

- `ST-24-04` can mirror the same draft-history and draft-continuity model for seating.
