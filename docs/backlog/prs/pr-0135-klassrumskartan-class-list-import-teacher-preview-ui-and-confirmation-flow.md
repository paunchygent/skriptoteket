---
type: pr
id: PR-0135
title: "Klassrumskartan: class-list import teacher preview UI and confirmation flow"
status: ready
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-02"
tags: ["frontend", "ux", "klassrumskartan", "import"]
acceptance_criteria:
  - "Given a teacher is on the overview screen, when they want to create a new class, then an 'Importera från fil' option is available alongside manual creation."
  - "Given the teacher selects a file, when the backend returns the `ClassListImportPreview`, then a modal or full-screen workflow displays the suggested class name and the parsed student list for review."
  - "Given the preview contains ambiguous rows, when the UI renders, then those rows are highlighted and the teacher is forced to either approve them as names, edit them, or explicitly discard them before saving."
  - "Given the teacher confirms the preview, when they click save, then the frontend submits the finalized, cleaned list to a new `POST /api/v1/apps/classroom.group-seating-studio/rosters/import-confirm` endpoint, and a standard Class Roster is created."
---

## Problem

The backend can now parse messy documents into a structured preview, but the teacher needs a UI to upload the file, review the automated parsing, correct mistakes (ambiguous rows), and finally confirm the creation of the class roster.

## Goal

Build the frontend UI for the preview-first import flow and the final backend endpoint to persist the confirmed roster.

## Locked design decisions

- **Entry point:** A new secondary button or dropdown option "Importera fil" next to the "Ny klass" button on the `Oversikt` (Overview) screen.
- **Workflow Phase 1 (Upload):** Standard file picker accepting `.xlsx, .csv, .txt, .pdf`. On select, show a loading state while calling `/import-preview`.
- **Workflow Phase 2 (Preview/Edit):**
  - Show the suggested class name in an editable text input.
  - Show a list of successfully parsed students (editable).
  - **Crucially:** Show a distinct visual section for `ambiguous_rows`. The teacher must have clear affordances to "Keep as name", "Edit", or "Discard" these rows.
- **Workflow Phase 3 (Confirm):** Clicking "Spara" sends the *final*, teacher-approved state (just class name and a list of strings/objects) to a new endpoint.
- **Final API:** `POST /api/v1/apps/classroom.group-seating-studio/rosters/import-confirm` (or similar). This endpoint bypasses the heuristics and directly creates the domain `Roster` entity, treating it exactly as if the teacher had typed it manually.

## Non-goals

- Implementing drag-and-drop file zones if a simple file input is sufficient for the first slice.
- Merging imported students into an *existing* roster (this story focuses on creating a *new* roster from a file).

## Implementation plan

1. **Backend:**
   - Add `POST /api/v1/apps/classroom.group-seating-studio/rosters/import-confirm` endpoint.
   - It accepts `ClassName` and `List[StudentName]`.
   - Reuses existing application commands for roster creation.
2. **Frontend Composable:**
   - Create `useClassListImportFlow.ts` to manage upload state, preview data, editing state of ambiguous rows, and final submission.
3. **Frontend Components:**
   - `PlannerImportAction.vue`: The trigger button and hidden file input.
   - `PlannerImportPreviewModal.vue`: The interactive review interface. It should use existing HuleEdu/Klassrumskartan design tokens (e.g., standard text inputs, delete icons).
4. **Integration:**
   - Wire the action into `PlannerRosterOverviewPanel.vue` or the main overview shell.

## Test plan

- **Backend:** Unit test the `/import-confirm` endpoint to ensure it creates the roster correctly.
- **Frontend:**
  - Component tests for `PlannerImportPreviewModal.vue` ensuring ambiguous rows can be discarded or edited, and that the final emitted payload is correct.
  - Integration/Playwright test: Click import, mock the preview response containing a good name and an ambiguous name, discard the ambiguous name, confirm, and verify the roster is created and visible in the overview.

## Rollback plan

- Disable the entry point button in the UI.
