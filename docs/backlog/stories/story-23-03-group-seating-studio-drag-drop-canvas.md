---
type: story
id: ST-23-03
title: "Klassrumskartan — Group Assignment Board"
status: done
owners: "agents"
created: 2026-03-20
updated: 2026-03-25
epic: "EPIC-23"
acceptance_criteria:
  - "Given a student is assigned to Group A, when the student is dragged to Group B, then the student appears only in Group B and their seat assignment is unchanged."
  - "Given a student has no group assignment, when the student is dragged from the roster drawer into a group, then a group assignment is created."
  - "Given a student is removed from a group, when the removal action is used, then the student remains in the roster and any seat assignment is unchanged."
---

## Context
This story focuses purely on the Group Assignment axis.

## Implementation Plan

### [ ] PR 1: Normalized Form State & Group Lifecycle
- **Intent**: Seed the local Pinia state to support group lists derived from normalized data, and allow teachers to create/manage group buckets.
- **Code Choice**: Model `groupsById` and `groupAssignmentsByStudentId`. Use `student_id` as the system key. Provide actions to explicitly add, remove, rename, and reorder Groups in the `PlanDraft`.

### [ ] PR 2: Group Board DOM Components
- **Intent**: Allow drag-and-drop construction of student groups from an "Unassigned" Catalog Pane.
- **Code Choice**: Build `GroupBoard.vue` integrating `vue-draggable-plus`. Define the Roster Drawer as a *Read-Only Catalog View*, meaning dragging from it does not physically remove the student from the roster list. Emit localized reducer actions like `assignStudentToGroup(studentId, groupId)`. Avoid mutating `v-model` arrays natively across axes.

## Implementation Summary (as of 2026-03-25)

- The grouping board shipped as the dedicated manual group-assignment surface for Klassrumskartan.
- Students can move between the unassigned pool and teacher-managed groups without coupling grouping to seat placement.
- The shipped board behavior now sits behind the later class-first workspace and grouping-draft lifecycle refinements recorded under `EPIC-24`.
