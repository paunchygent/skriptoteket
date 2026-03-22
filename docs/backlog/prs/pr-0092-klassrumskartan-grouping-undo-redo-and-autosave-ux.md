---
type: pr
id: PR-0092
title: "Klassrumskartan: grouping undo-redo and autosave UX"
status: in_progress
owners: "agents"
created: 2026-03-22
updated: 2026-03-22
stories:
  - "ST-24-03"
tags: ["frontend", "backend", "api"]
acceptance_criteria:
  - "The teacher can undo or redo recent grouping steps directly inside the grouping workspace without being exposed to separate saved-item jargon."
  - "Undo and redo operate on meaningful grouping actions such as move, swap, add/remove group, rename group, and randomize."
  - "The current compact autosave badge remains in place as low-noise workspace status rather than being replaced with a larger save panel."
  - "The grouping workspace respects the bounded recent-history limit and communicates when undo or redo is no longer available."
  - "`Nytt grupputkast` remains a draft-lifecycle boundary and is not treated as an undoable in-draft edit step."
  - "Frontend and backend tests cover undo, redo, autosave feedback, and recent-history bounds."
---

## Problem

Even with a bounded grouping draft-history contract available, the teacher still needs a clean,
workspace-first way to use it:

- undo the last change
- redo a reverted change
- understand that work is autosaved
- avoid thinking in terms of separate saved drafts or artifact versions

If that experience is surfaced using technical lifecycle language, the app will again feel much
more complex than the current document-like workflow requires.

## Goal

Add the teacher-facing grouping workspace controls for undo/redo and autosave:

- undo and redo are simple workspace actions
- autosave remains compact status, not a big save panel
- recent history is visible through controls, not through a pile of saved items

## Non-goals

- File-vault projection/export delivery.
- Seating undo/redo flows.
- Exposing bounded recent history as a major class-level archive.
- Advanced compare/version browser UX.
- Redesigning the shared top panel or replacing the existing autosave badge with a new visual pattern.
- Treating `Nytt grupputkast` as part of the same undo/redo chain.

## Checklist

- [x] Add undo and redo controls to the grouping workspace.
- [x] Keep the existing compact autosave badge pattern and make it coexist cleanly with undo/redo.
- [x] Record meaningful grouping actions into recent history.
- [x] Respect the configured recent-history depth in the UI.
- [x] Keep `Nytt grupputkast` outside the undo/redo chain.
- [x] Add frontend/backend tests for undo, redo, and autosave feedback behavior.
- [ ] Restore the full Klassrumskartan Playwright smoke to green after the unrelated `Avsluta`-to-landing path is corrected.

## Implementation plan

- Extend the grouping workspace controls with explicit grouping-only undo/redo actions.
- Treat these actions as workspace editing controls rather than as navigation to older saved items.
- Orchestrate undo/redo in the Pinia store:
  - flush pending autosave first
  - call the backend undo/redo endpoint
  - rehydrate the returned workspace, including backend-owned history availability
- Keep the current compact autosave badge pattern in the shared top panel and avoid redesigning it unless a bug forces a tiny polish adjustment.
- Allow undo to become available immediately when local grouping changes are pending, while still keeping backend history as the source of truth for persisted availability.
- Make availability explicit:
  - undo disabled when no earlier step exists
  - redo disabled when no later step exists
- Ensure actions like `Slumpa`, move, swap, rename, and add/remove group are treated as meaningful
  recent-history steps.
- Keep `Nytt grupputkast` as a draft-lifecycle action that supersedes the current active grouping draft rather than as an undoable workspace edit.
- Prefer grouping-local UI wiring in the grouping workspace surface; do not broaden the shared shell with speculative seating undo/redo chrome.

## Test plan

- Backend/API:
  - undo current grouping step
  - redo reverted grouping step
- Frontend:
  - undo/redo controls enable and disable correctly
  - the compact autosave badge remains visible and distinct from undo/redo
  - history bounds are respected
  - `Nytt grupputkast` is not presented or treated as part of undo/redo
- Manual:
  - create a grouping, move students, rename groups, randomize, undo several times, redo several
    times, and confirm the flow remains understandable without any separate saved-item model

## Rollback plan

- Revert the grouping undo/redo UI if it confuses autosave with navigation or destabilizes
  grouping edits, while preserving the backend draft-history contract for later reintroduction.

## Implementation status (2026-03-22)

- Local redo/undo fallback state was removed so backend `history_status` is again the authoritative redo source.
- The browser-level teacher path now works locally:
  - rename first group
  - `Ångra`
  - `Gör om`
  - custom name returns
- The Pinia store now only adds one local affordance on top of backend truth: `Ångra` stays clickable while a grouping edit is pending autosave, because the action flushes that pending save before calling backend undo.
- The broader Playwright baseline is still red, but for a separate reason: after `Avsluta`, the app remains in the class workspace instead of returning to the landing screen, so the smoke cannot reach the landing-page `Avsluta utkast` cleanup CTA. That issue should be fixed before this PR is closed as `done`.

## Follow-up direction

- `PR-0093` tightens grouping draft continuity and secondary class-history behavior so new-draft
  creation, resume, and prior draft browsing stay clear without competing with undo/redo.
