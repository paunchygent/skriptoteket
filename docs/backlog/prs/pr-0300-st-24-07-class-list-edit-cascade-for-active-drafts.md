---
type: pr
id: PR-0300
title: "ST-24-07: class-list edit cascade for active drafts"
status: done
owners: "agents"
created: 2026-05-05
updated: 2026-05-05
stories:
  - "ST-24-07"
tags: ["backend", "klassrumskartan", "roster", "draft-lifecycle"]
acceptance_criteria:
  - "Given a class list has active grouping or seating drafts, when the teacher adds students or edits existing student display names and saves the class list, then the save succeeds rather than being blocked by active draft existence alone."
  - "Given the teacher removes students from a class list and saves, when those student ids appear in active or historical grouping/seating draft assignments, then those references are removed in the same transaction as the roster update."
  - "Given removed students appear in roster-owned smart rules, when the class list save completes, then near-teacher preferences and fixed-seat rules for removed students are deleted, relationship rules drop removed students, and relationship rules with fewer than two remaining students are deleted."
  - "Given no removed student ids are present, when the class list save completes, then draft cleanup and smart-rule writes are not performed."
  - "Given the class list itself is deleted, when the delete confirmation is accepted, then the existing roster-delete cascade remains unchanged and active draft existence is not treated as a separate blocker."
---

## Problem

Klassrumskartan normally keeps one active grouping draft and one active seating draft per class.
The class-list edit path incorrectly treated active draft existence as proof that the class list
could not change, returning:

`Du kan inte ändra eleverna i klasslistan eftersom ett aktivt utkast fortfarande använder den.`

That guard second-guessed a deliberate `Spara` action and contradicted the roster-delete lifecycle,
where destructive confirmation already authorizes cascading dependent draft state.

## Goal

Respect saved class-list edits while keeping dependent planner state valid:

- allow student additions and display-name edits while active drafts exist
- cascade removed student ids out of draft assignments and draft history snapshots
- cascade removed student ids out of roster-owned smart rules
- delete relationship rules that become invalid after pruning
- keep roster deletion on the existing destructive-confirmation cascade path

## Non-goals

- Adding a new frontend confirmation step for student removal.
- Blocking class-list edits because a draft container exists.
- Changing grouping or seating draft lifecycle semantics beyond removed-student cleanup.
- Changing fixed-seat solver behavior; that remains owned by `PR-0297`.

## Implementation

- Removed the active-draft-existence guard from the roster update handler.
- Added a roster-student cleanup service at the application boundary.
- Added a focused draft-reference cleanup repository that removes deleted student ids from:
  - current grouping assignments
  - current seating assignments
  - bounded draft history snapshots
- Pruned roster-owned smart rules on removed student ids:
  - remove seating preferences for deleted students
  - remove fixed-seat rules for deleted students
  - remove deleted students from keep-near / keep-apart rules
  - drop relationship rules with fewer than two remaining students
- Split oversized touched modules so the implementation complies with the repo LoC/SRP mandate.

## Verification

- `pdm run pytest tests/unit/application/apps/classroom_planner/test_roster_updates.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/application/apps/classroom_planner/test_smart_rules.py tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/infrastructure/repositories/test_classroom_planner_roster_student_cleanup.py tests/unit/infrastructure/repositories/test_classroom_planner_smart_rules.py tests/unit/web/apps/classroom_planner/test_smart_rules_api.py -q`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_fixed_seats.py -q`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-test -- --run classroomPlannerRouteShellWorkspace`
- `pdm run docs-validate`
- `git diff --check`

## Rollback

Reinstate the old active-draft conflict guard in the roster update handler and remove the roster
student cleanup service/repository wiring. This is not preferred because it would restore the
incorrect block for ordinary active draft containers.
