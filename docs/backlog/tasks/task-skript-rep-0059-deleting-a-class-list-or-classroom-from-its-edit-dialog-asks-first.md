---
type: task
id: TASK-SKRIPT-REP-0059
title: Deleting a class list or classroom from its edit dialog asks first
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-29'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - Radera in Redigera klasslista opens the same confirmation Översikt uses for a class list, naming the class; the class list is deleted only after Ta bort klasslista
  - Radera in Redigera klassrum opens the same confirmation Översikt uses for a classroom; the classroom is deleted only after its confirm button
  - Avbryt in the confirmation leaves the class list or classroom and the edit dialog as they were, for signed-in teachers and guests
backlog_document_profile: contract-derived
---

## Implementation Contract

The Mac staging walk of TASK-SKRIPT-REP-0057 at `cbbf5d969` showed that Radera in Klassrumskartan's "Redigera
klasslista" dialog deletes the class list at once, with no confirmation and no undo (`removeRoster` in
`useRosterForm.ts` sends the DELETE directly). Deleting from Översikt already asks first through
`PlannerConfirmationDialog` (`ClassroomPlannerView.vue:296-307`, `ClassroomPlannerGuestOverviewView.vue:338`). The
user decided on 2026-10-29 that deleting a class list or a classroom always asks first.

- Actor: a signed-in teacher or a guest editing a class list or a classroom.
- Change: the delete glyph in `CreateRosterModal.vue` and `CreateRoomTemplateModal.vue` opens the same
  `PlannerConfirmationDialog` with the same copy Översikt uses for that item (class name, dependent drafts);
  the delete runs only on its confirm button, and its error shows in the dialog as in Översikt.
- Avbryt closes the confirmation and leaves the edit dialog open and unchanged.
- Non-goals: an undo notice, other delete actions, Översikt's own delete flow.

## Contract Inputs

- User decision 2026-10-29 (AskUserQuestion: ask before deleting, for class lists and classrooms).
- Mac walk record `~/Repos/Skriptoteket/.artifacts/staging-walk-rep-0057-cbbf5d969/walk-record.md` (item 3).
- `PlannerConfirmationDialog` and the Översikt delete flow in `classroomPlannerRouteShellOverviewCrud.ts`.

## Core Vertical And Performance

One junior unit: tap the delete glyph in the edit dialog, see the confirmation, confirm, the item is gone; or
cancel, nothing changes. Reuse the existing dialog and copy; no new component or endpoint.

## Validation

- Focused Vitest specs for both modals: delete opens the confirmation and sends no request; confirm sends the
  delete; cancel sends nothing and keeps the edit dialog; the guest path behaves the same.
- A Mac staging check on a disposable class list and classroom.

## Stop Conditions

- The confirmation cannot be shown from the edit dialog without changing Översikt's delete flow.

## Decided Contract Terms

| ID  | Decided contract term                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------ |
| D1  | Deleting a class list or classroom from its edit dialog asks first (user decision 2026-10-29).         |
| D2  | The edit dialogs reuse `PlannerConfirmationDialog` with the copy Översikt uses; no new dialog or copy. |
| D3  | Proof is focused specs and a Mac staging check; light route, no review.                                |
