---
type: pr
id: PR-0175
title: "Klassrumskartan: class-list import drag-and-drop drop zone in create/edit modal"
status: in_progress
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
stories:
  - "ST-26-02"
tags: ["frontend", "ux", "klassrumskartan", "import", "drag-drop"]
acceptance_criteria:
  - "Given a teacher opens `Ny klasslista` or `Redigera klasslista`, when they read the class-list import guidance, then a visible drag-and-drop drop zone appears directly beneath the supported file-type explanation while the existing picker button remains available."
  - "Given a teacher drops one supported roster file (`.xlsx`, `.xls`, `.csv`, `.tsv`, `.txt`, `.pdf`) onto the drop zone, when the drop completes, then the existing import-preview request runs and the preview-prefill flow behaves exactly like picker-based import."
  - "Given drag-and-drop is unavailable, skipped, or invalid input is dropped, when the teacher still needs to import, then the click-to-choose fallback continues to work and the modal keeps the current preview/manual-edit behavior without introducing backend or contract changes."
---

## Problem

The current class-list import flow in the shared create/edit roster modal is functionally strong but
still forces the teacher through the file picker. That adds friction in the exact workflow where the
teacher often already has the source file on screen or on the desktop and expects to drag it
straight into the app.

There is also now a teacher-facing wording mismatch: the Klassrumskartan guide says the teacher can
"dra in" the class list, but the shipped modal still exposes only the hidden file input plus button
trigger.

Technical note for implementation: this should be planned as browser-native drag/drop of a `File`
object, not as local filesystem-path capture. The UX goal is "drop instead of browse", while the
actual upload contract remains the same multipart file submission used today.

## Goal

Add a small, obvious drag-and-drop affordance to the existing class-list import block inside the
shared create/edit roster modal so teachers can import by dropping a file directly beneath the
supported-file guidance, without changing the backend contract or the rest of the preview-first
workflow.

## Status note (2026-03-31)

Focused Vitest coverage and a live Playwright proof are already recorded in `.agents/handoff.md`,
but this doc still stops short of an explicit shipped/done callout. Its `in_progress` status is
left unchanged for now so that a human can decide whether the slice is fully closed.

## Non-goals

- Introducing a new backend API or changing the `import-preview` contract.
- Supporting multi-file import, folder drop, or queue-style upload management.
- Reworking parser heuristics, ambiguous-row handling, or roster save semantics.
- Moving class-list import back out to a separate overview-level action.
- Treating local file paths as part of the product contract.

## Implementation plan

1. Keep `ST-26-02` as the governing story and implement this as a focused frontend follow-up in the
   existing `CreateRosterModal.vue` surface used by both `Ny klasslista` and `Redigera klasslista`.
2. Add a visible drop zone directly beneath the supported-file explanation in the import card and
   keep the current `Importera från fil` button as the explicit click fallback.
3. Add a small shared modal-local helper such as `handleImportFile(file)` so both the hidden file
   input change handler and the new drop handler reuse the same upload path and remain DRY.
4. Use native browser drag events (`dragenter`/`dragover`/`dragleave`/`drop`) with a clear active
   visual state, and keep drag/drop additive rather than required so keyboard/mobile users still
   succeed through the existing picker button.
5. Keep the current `useClassListImportFlow.ts` transport seam and `POST
   /api/v1/apps/classroom.group-seating-studio/rosters/import-preview` request untouched.
6. Handle invalid input conservatively for this slice:
   - one file at a time
   - ignore folder-style assumptions
   - keep or show clear inline feedback if an invalid/empty drop occurs
7. Align the teacher guidance copy if needed so the modal and the guide both explicitly support
   "dra och släpp" plus click-to-choose behavior.

## Test plan

- Frontend component tests in `CreateRosterModal.spec.ts` for:
  - successful single-file drop using the existing preview flow
  - drag-active state entering/leaving the drop zone
  - picker-based import still working unchanged after the new affordance is added
- Live local functional proof in both create and edit modes:
  - open `Ny klasslista`
  - open `Redigera klasslista`
  - drop a supported file and verify the preview prefills as before
- Record the exact live verification command/manual proof in `.agents/handoff.md` when the
  implementation lands.

## Rollback plan

- Remove the drop-zone markup and drag-event handling from the shared roster modal.
- Keep the existing hidden input plus `Importera från fil` button path intact.
