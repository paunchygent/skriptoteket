---
type: pr
id: PR-0177
title: "ST-29-09: rule visibility and tool-feedback continuity"
status: in_progress
owners: "agents"
created: 2026-03-30
updated: 2026-03-30
stories:
  - "ST-29-09"
tags: ["frontend", "ux", "klassrumskartan", "smart-rules", "room-editor"]
dependencies:
  - "EPIC-29"
  - "PR-0155"
  - "PR-0157"
  - "PR-0161"
acceptance_criteria:
  - "The seating toolbar no longer renders a redundant active-rule count pill when the map already shows the active rules."
  - "The classroom editor tool palette exposes explicit active-tool feedback aligned with the rules rail."
  - "Smart-rule markers are visible on student bars in grouping and seating, and in grouping they remain visible after assignment inside group cards."
  - "Focused frontend tests plus a live local UI check prove the new feedback surfaces and grouped-student marker continuity."
---

## Problem

Teachers currently lose UI trust in three adjacent places:

1. `Sittplatser` repeats rule state through a pill that adds chrome without new information.
2. the classroom editor tool palette is still weaker than the rules rail at confirming which tool
   is active.
3. `Grupper` drops smart-rule visibility once students move from the ungrouped list into their
   actual assigned group cards.

## Goal

Ship one small UI continuity slice that:

- removes the redundant seating rule-count pill,
- aligns room-editor tool feedback with the established rules-rail pattern, and
- keeps smart-rule markers visible on the student bars wherever those rows appear.

## Non-goals

- Changing smart-rule persistence, labels, or solver behavior.
- Reopening the rules-workspace layout doctrine from `ST-29-06`.
- Redesigning the full classroom editor modal beyond tool-feedback continuity.

## Implementation plan

1. Seating toolbar cleanup
   - Remove the active-rule count pill from `PlannerSeatingWorkspaceToolbar.vue`.
   - Keep `Smart`, `Regler`, and `Använd historik` unchanged.

2. Classroom editor tool-feedback alignment
   - Update `RoomTemplateEditorSidebar.vue` so the tool palette uses the shared active/idle choice
     language and a local active-tool feedback surface.
   - Keep the editor modal bounded; do not add new drawers, banners, or status pills.

3. Student-bar rule visibility
   - Reuse the existing smart-rule marker presentation helpers.
   - Pass rule-marker data into the grouping student pool and grouped student cards so markers stay
     visible after assignment.
   - Preserve the current seating student-pool marker semantics.

4. Verification
   - Add focused Vitest coverage for the room-editor tool palette and grouped-student marker
     continuity.
   - Run a live local browser check at `http://127.0.0.1:5173`.

## Test plan

- `pdm run fe-test -- --run src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/components/RoomTemplateEditorSidebar.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- Live check:
  - `pdm run python -m scripts.playwright_pr_0177_rule_visibility_and_tool_feedback_check --base-url http://127.0.0.1:5173`

## Rollback plan

- Revert the seating-toolbar, room-editor, and grouped-student marker changes together if the new
  continuity pattern proves misleading.
- Keep the underlying smart-rule data flow and rules-workspace contract untouched if rollback is
  required.
