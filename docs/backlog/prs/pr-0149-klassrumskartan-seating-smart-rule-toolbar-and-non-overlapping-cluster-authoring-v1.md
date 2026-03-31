---
type: pr
id: PR-0149
title: "Klassrumskartan: seating smart-rule toolbar and non-overlapping cluster authoring v1"
status: done
owners: "agents"
created: 2026-03-27
updated: 2026-03-31
stories:
  - "ST-27-03"
tags: ["frontend", "api-contract", "state", "ux", "klassrumskartan", "smart-assignment"]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0147"
  - "PR-0151"
acceptance_criteria:
  - "Given the teacher is in `Sittplatser` and opens the smart-rule surface, when they choose one smart tool, then exactly one tool is active at a time and incomplete selections are cleared by tool changes, `Esc`, or `Rensa markering`."
  - "Given the teacher chooses `Närmare läraren`, when they click one student tile, then that student's unary seating rule toggles on or off immediately without requiring a separate commit form."
  - "Given the teacher chooses `Håll isär` or `Håll nära`, when they select two or more student tiles and confirm the rule, then one visible relationship cluster is created from that temporary selection and the selection clears while the tool stays active."
  - "Given the teacher tries to create a visible relation rule using a student who already belongs to another `Håll isär` or `Håll nära` cluster, when they attempt to commit the new rule, then V1 blocks that overlapping cluster and shows a short teacher-facing explanation."
  - "Given visible smart rules exist in seating, when the workspace renders, then the teacher can see those rules from the main seating surface through tile markers and a visible rule summary area rather than a drawer-first editing flow."
  - "Given `Use history` exists in the smart seating contract, when this slice ships, then it remains background behavior only and is not introduced as a primary editing control in the toolbar flow."
---

## Problem

`PR-0147` made the smart seating contract honest, but the planner still lacks the first real
teacher-facing authoring flow for that contract. The next slice needs to establish the visible
interaction model in seating without reintroducing drawer-first editing or relationship-conflict
complexity that V1 is not ready to solve.

## Goal

Implement the first class-wide smart-rule authoring surface in `Sittplatser` with:

- one active toolbar tool at a time
- unary click-to-toggle `Närmare läraren`
- multi-select plus explicit commit for `Håll isär` / `Håll nära`
- non-overlapping visible relationship clusters
- visible rule summary from the main seating workspace

This slice defines the seating authoring UX, but the authored rules themselves are class-global and
roster-owned rather than draft-owned.

## Landing note

The current local implementation for this slice is intentionally not merge-ready on its own after
the ownership correction. It still needs the `PR-0151` boundary reset so the existing UI stops:

- persisting smart rules through draft PATCH/autosave
- treating draft-local `Smart` as the authoring gate for roster-global rules

## Non-goals

- Shipping grouping smart-rule authoring in this PR.
- Exposing `Use history` as a primary editable control.
- Solving overlapping relationship clusters.
- Adding line-drawing / graph visuals between students.
- Delivering the full backend smart solver or explanation lane.
- Cementing draft-owned smart-rule persistence as a long-term model.

## Implementation plan

1. Lock the UI state model first.
   - Add one active smart-tool state plus temporary relation selection state in the seating store.
   - Keep `Närmare läraren` separate from relationship-cluster membership.
   - Enforce one visible relationship-cluster membership per student in the client state model.
   - Keep the client/store boundary compatible with roster-global smart-rule loading rather than
     assuming draft PATCH is the authoritative persistence path.

2. Add seating-toolbar rule authoring.
   - Add or extend a seating smart-toolbar surface with:
     - `Håll isär`
     - `Håll nära`
     - `Närmare läraren`
     - `Rensa markering`
   - Keep one active tool at a time.
   - Clear incomplete selections on tool change and explicit reset.

3. Implement tile interaction rules.
   - `Närmare läraren`: click tile toggles the unary rule immediately.
   - `Håll isär` / `Håll nära`: click tiles builds a temporary 2+ student selection.
   - Add one explicit commit action for relation-cluster creation.
   - Keep the active relation tool selected after a successful commit.

4. Add visible rule-summary rendering.
   - Render one main summary surface in the seating workspace for current rules.
   - Support deleting rules from that summary.
   - Keep the metadata drawer secondary; do not route primary rule editing through it.

5. Keep `Use history` background-only.
   - Preserve the existing contract/state where relevant.
   - Do not add a new toolbar toggle or settings drawer entry for it in this slice.

## PR-sized execution checklist

- [ ] Update/add frontend interaction tests first:
  - seating workspace component tests
  - `useClassroomState` smart-rule state tests
  - shell tests if toolbar placement changes
- [ ] Implement seating smart-tool state in:
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
- [ ] Implement/extend seating toolbar + summary components:
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
  - any new seating smart-rule toolbar/summary component files created for this slice
- [ ] Retarget API/store serialization through `PR-0151` so this UI no longer depends on draft-owned rule persistence
- [ ] Run frontend verification plus live Playwright proof
- [ ] Record verification in `.agents/handoff.md`

## Test plan

- `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts`
- `pdm run fe-test -- --run <new-or-updated seating workspace spec files>`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`

## Rollback plan

- Revert the toolbar/rule-authoring UI slice together if the interaction model proves misleading.
- Do not reintroduce drawer-first smart editing as a rollback shortcut.
- Keep the ADR/story/task docs updated so any future replacement still starts from the locked V1
  decisions.
